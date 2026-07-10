from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from memu.blob.folder import infer_modality

if TYPE_CHECKING:
    from memu.app.service import Context
    from memu.database.interfaces import Database
    from memu.database.models import RecallFile, Resource


class AgenticMixin:
    if TYPE_CHECKING:
        _get_context: Callable[[], Context]
        _get_database: Callable[[], Database]
        _normalize_where: Callable[[Mapping[str, Any] | None], dict[str, Any]]
        _model_dump_without_embeddings: Callable[[BaseModel], dict[str, Any]]
        _ensure_categories_ready: Callable[[Context, Database, Mapping[str, Any] | None], Awaitable[None]]
        _get_embedding_client: Callable[..., Any]
        user_model: type[BaseModel]

    async def list_all_recall_files(
        self,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """List RecallFiles across every track without workflow orchestration.

        Unlike :meth:`CRUDMixin.list_recall_files`, this does not force the
        ``track="memory"`` filter (ADR 0006), so skill-track files are included,
        and it queries the repository directly instead of running a workflow.
        """
        store = self._get_database()
        where_filters = self._normalize_where(where)
        categories = store.recall_file_repo.list_categories(where_filters)
        categories_list = [self._model_dump_without_embeddings(category) for category in categories.values()]
        return {"categories": categories_list}

    async def commit_results(
        self,
        *,
        recall_files: list[dict[str, Any]] | None = None,
        resource: list[dict[str, Any]] | None = None,
        user: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist externally-prepared resources and recall files into the store.

        This mirrors the persistence half of :meth:`MemorizeWorkspaceMixin.memorize_workspace`
        but takes items that were already preprocessed/synthesized off-service (see
        ``skills/scripts/commit_results.py``), so it runs no ingest/preprocess/LLM steps and
        no workflow — just create-or-update straight into storage:

        - ``resource`` — a list of ``{path, description}`` records. Each is a
          :class:`Resource` keyed by ``url`` (``= path``); the description becomes the
          embedded caption used for INDEX/resource recall.
        - ``recall_files`` — a list of ``{name, track, description, content}`` records. Each
          is a :class:`RecallFile` keyed by ``name`` within its ``track`` (``memory``/``skill``),
          with the same track-specific segment (re)generation as the workspace path.
        """
        store = self._get_database()
        user_scope = self.user_model(**user).model_dump() if user is not None else None
        embed_client = self._get_embedding_client("embedding")

        committed_resources = await self._commit_resources(
            resource or [], store=store, user_scope=user_scope, embed_client=embed_client
        )
        committed_files = await self._commit_recall_files(
            recall_files or [], store=store, user_scope=user_scope, embed_client=embed_client
        )
        return {
            "resources": [self._model_dump_without_embeddings(r) for r in committed_resources],
            "recall_files": [self._model_dump_without_embeddings(f) for f in committed_files],
        }

    async def _commit_resources(
        self,
        resources: list[dict[str, Any]],
        *,
        store: Database,
        user_scope: dict[str, Any] | None,
        embed_client: Any,
    ) -> list[Resource]:
        """Create-or-update each ``{path, description}`` as a ``Resource`` keyed by url.

        ``ResourceRepo`` has no in-place update, so an "update" is a delete-then-create:
        any existing resource sharing this url (and its file provenance links) is dropped
        before the fresh record is created. Mirrors
        :meth:`MemorizeWorkspaceMixin._create_resource_with_caption`.
        """
        where = user_scope or None
        committed: list[Resource] = []
        for item in resources:
            url = (item.get("path") or "").strip()
            if not url:
                continue
            caption = (item.get("description") or "").strip() or None

            # Create-or-update keyed by url: drop any prior resource for this url first.
            stale = [res for res in store.resource_repo.list_resources(where=where).values() if res.url == url]
            for res in stale:
                store.recall_file_resource_repo.unlink_resource(res.id)
                store.resource_repo.delete_resource(res.id)

            caption_embedding = (await embed_client.embed([caption]))[0] if caption else None
            res = store.resource_repo.create_resource(
                url=url,
                modality=infer_modality(url) or "document",
                local_path=url,
                caption=caption,
                embedding=caption_embedding,
                user_data=dict(user_scope or {}),
            )
            committed.append(res)
        return committed

    async def _commit_recall_files(
        self,
        recall_files: list[dict[str, Any]],
        *,
        store: Database,
        user_scope: dict[str, Any] | None,
        embed_client: Any,
    ) -> list[RecallFile]:
        """Create-or-update each ``{name, track, description, content}`` as a ``RecallFile``.

        Keyed by ``name`` within the record's ``track`` (``memory``/``skill``). New files embed
        their ``name: description`` for file-level recall; existing files keep their embedding
        and only take the new content. Segments are then reconciled per track. Mirrors the
        persist path of :meth:`MemorizeWorkspaceMixin._synthesize_file_ops`.
        """
        user_data = dict(user_scope or {})
        committed: list[RecallFile] = []
        for item in recall_files:
            name = (item.get("name") or "").strip()
            if not name:
                continue
            file_track = item.get("track") or "memory"
            description = (item.get("description") or "").strip()
            content = (item.get("content") or "").strip()

            existing = store.recall_file_repo.list_categories(where={**user_data, "track": file_track})
            file = {f.name: f for f in existing.values()}.get(name)
            if file is None:
                emb_text = f"{name}: {description}" if description else name
                embedding = (await embed_client.embed([emb_text]))[0]
                file = store.recall_file_repo.get_or_create_category(
                    name=name,
                    description=description,
                    embedding=embedding,
                    user_data=user_data,
                    track=file_track,
                )
            file = store.recall_file_repo.update_category(category_id=file.id, content=content)
            await self._commit_sync_file_segments(
                file=file,
                file_track=file_track,
                store=store,
                user_scope=user_data,
                embed_client=embed_client,
            )
            committed.append(file)
        return committed

    @staticmethod
    def _commit_segment_texts_for_file(file: RecallFile, file_track: str) -> list[str]:
        """Compute a file's searchable segment texts (ADR 0007 L2 items), track-specific.

        Mirrors :meth:`MemorizeWorkspaceMixin._segment_texts_for_file`:

        - ``skill``: a single ``name: ...\\ndescription: ...`` segment for the whole skill.
        - ``memory``: one segment per content line, skipping blank lines and markdown
          headings, de-duplicated while preserving order.
        """
        if file_track == "skill":
            return [f"name: {file.name}\ndescription: {file.description}"]

        texts: list[str] = []
        for line in (file.content or "").split("\n"):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            texts.append(stripped)
        return list(dict.fromkeys(texts))

    async def _commit_sync_file_segments(
        self,
        *,
        file: RecallFile,
        file_track: str,
        store: Database,
        user_scope: dict[str, Any],
        embed_client: Any,
    ) -> None:
        """Reconcile a file's stored segments with its freshly computed segment texts.

        Drop-and-add on the difference only: segments whose text disappeared are deleted and
        only genuinely new texts are embedded and inserted, so unchanged lines keep their
        embedding. Mirrors :meth:`MemorizeWorkspaceMixin._sync_file_segments` (single file).
        """
        new_texts = self._commit_segment_texts_for_file(file, file_track)
        existing = store.recall_file_segment_repo.list_segments_for_file(file.id)
        existing_texts = {seg.text for seg in existing}
        new_set = set(new_texts)

        for seg in existing:
            if seg.text not in new_set:
                store.recall_file_segment_repo.delete_segment(seg.id)

        to_add = [text for text in new_texts if text not in existing_texts]
        if not to_add:
            return
        vecs = await embed_client.embed(to_add)
        for text, vec in zip(to_add, vecs, strict=True):
            store.recall_file_segment_repo.create_segment(
                recall_file_id=file.id, track=file_track, text=text, embedding=vec, user_data=dict(user_scope)
            )
