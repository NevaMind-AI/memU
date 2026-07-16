from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from memu.vector import cosine_topk

if TYPE_CHECKING:
    from memu.app.settings import ProgressiveRetrieveConfig
    from memu.database.interfaces import Database
    from memu.database.models import RecallFile, Resource


async def _embed_one(embed_client: Any, text: str) -> list[float]:
    """One text in, one vector out.

    ``embed`` returns ``(vectors, raw_response)`` — the raw response carries
    provider usage metadata (see :class:`memu.embedding.base.EmbeddingClient`).
    Every call site here wants just the vector; indexing the tuple with ``[0]``
    would hand back the whole vectors list instead.
    """
    vectors, _ = await embed_client.embed([text])
    return vectors[0]


class AgenticMixin:
    if TYPE_CHECKING:
        _get_database: Callable[[], Database]
        _normalize_where: Callable[[Mapping[str, Any] | None], dict[str, Any]]
        _model_dump_without_embeddings: Callable[[BaseModel], dict[str, Any]]
        _get_embedding_client: Callable[..., Any]
        progressive_retrieve_config: ProgressiveRetrieveConfig
        user_model: type[BaseModel]

    async def list_all_recall_files(
        self,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """List RecallFiles across every track.

        No ``track`` filter is forced (ADR 0006), so skill-track files are
        included alongside memory-track ones; the repository is queried directly.
        """
        store = self._get_database()
        where_filters = self._normalize_where(where)
        categories = store.recall_file_repo.list_categories(where_filters)
        categories_list = [self._model_dump_without_embeddings(category) for category in categories.values()]
        return {"categories": categories_list}

    async def progressive_retrieve(
        self,
        query: str,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Single-shot, LLM-free retrieval over the segment/file/resource layers.

        The stages run sequentially in-line: the query is embedded once and used
        to rank two layers by vector similarity; no intention routing,
        sufficiency checks, or summarization:

        * ``segments``: :class:`RecallFileSegment` slices ranked by embedding,
          ``file.top_k`` of them.
        * ``files``: the :class:`RecallFile`\\ s pointed to by those segments — not
          a ranked search, just a roll-up. Each file's score is the max score of
          the segments that point to it.
        * ``resources``: workspace-track resources ranked by embedding,
          ``resource.top_k`` of them.

        Returns ``segments``, ``files``, and ``resources``.
        """
        if not query or not query.strip():
            raise ValueError("empty_query")
        store = self._get_database()
        where_filters = self._normalize_where(where)
        config = self.progressive_retrieve_config
        embed_client = self._get_embedding_client("embedding")
        query_vector = await _embed_one(embed_client, query)

        segment_hits, segment_pool = self._recall_segments(
            store=store, where_filters=where_filters, query_vector=query_vector, enabled=config.file.enabled
        )
        file_hits, file_pool, file_resource_urls = self._collect_files(
            store=store, where_filters=where_filters, segment_hits=segment_hits, segment_pool=segment_pool
        )
        resource_hits, resource_pool = self._recall_resources(
            store=store, where_filters=where_filters, query_vector=query_vector, enabled=config.resource.enabled
        )

        files = self._materialize_hits(file_hits, file_pool)
        for file in files:
            file["resource_urls"] = file_resource_urls.get(file["id"], [])
        return {
            "segments": self._materialize_hits(segment_hits, segment_pool),
            "files": files,
            "resources": self._materialize_hits(resource_hits, resource_pool),
        }

    def _recall_segments(
        self,
        *,
        store: Database,
        where_filters: dict[str, Any],
        query_vector: list[float],
        enabled: bool,
    ) -> tuple[list[tuple[str, float]], dict[str, Any]]:
        """Rank :class:`RecallFileSegment` slices by embedding similarity.

        The segment repo has no vector search, so the stored segment embeddings
        are ranked directly, optionally scoped to the configured tracks via the
        denormalized ``track``.
        """
        if not enabled:
            return [], {}

        segment_where = dict(where_filters)
        tracks = self.progressive_retrieve_config.file.tracks
        if tracks:
            segment_where["track__in"] = list(tracks)
        segment_pool = {seg.id: seg for seg in store.recall_file_segment_repo.list_segments(segment_where)}
        segment_hits = cosine_topk(
            query_vector,
            [(sid, seg.embedding) for sid, seg in segment_pool.items()],
            k=self.progressive_retrieve_config.file.top_k,
        )
        return segment_hits, segment_pool

    def _collect_files(
        self,
        *,
        store: Database,
        where_filters: dict[str, Any],
        segment_hits: list[tuple[str, float]],
        segment_pool: dict[str, Any],
    ) -> tuple[list[tuple[str, float]], dict[str, Any], dict[str, list[str]]]:
        """Roll the ranked segments up to their files (no ranked file search).

        Every file pointed to by a top segment is returned; a file's score is the
        max score across the segments that point to it.
        """
        file_pool = store.recall_file_repo.list_categories(where_filters)

        file_scores: dict[str, float] = {}
        for seg_id, score in segment_hits:
            seg = segment_pool.get(seg_id)
            if seg is None:
                continue
            fid = seg.recall_file_id
            if fid not in file_pool:
                continue
            score = float(score)
            if fid not in file_scores or score > file_scores[fid]:
                file_scores[fid] = score

        # Preserve descending-score order so the response reads best-first.
        file_hits = sorted(file_scores.items(), key=lambda kv: kv[1], reverse=True)
        file_resource_urls = self._collect_file_resource_urls(store, where_filters, file_pool)
        return file_hits, file_pool, file_resource_urls

    @staticmethod
    def _collect_file_resource_urls(
        store: Database, where_filters: dict[str, Any], file_pool: dict[str, Any]
    ) -> dict[str, list[str]]:
        """Map each file id to the URLs of the resources linked to it.

        Resolves the ``RecallFileResource`` link table (file -> resource) and the
        resource records (resource -> url) within the current scope, surfacing url
        strings only.
        """
        resources = store.resource_repo.list_resources(where_filters)
        file_resource_urls: dict[str, list[str]] = {}
        for rel in store.recall_file_resource_repo.list_relations(where_filters):
            if rel.file_id not in file_pool:
                continue
            resource = resources.get(rel.resource_id)
            if resource is None:
                continue
            file_resource_urls.setdefault(rel.file_id, []).append(resource.url)
        return file_resource_urls

    def _recall_resources(
        self,
        *,
        store: Database,
        where_filters: dict[str, Any],
        query_vector: list[float],
        enabled: bool,
    ) -> tuple[list[tuple[str, float]], dict[str, Any]]:
        """Rank workspace-track resources by embedding similarity.

        Only ``track="workspace"`` resources (the kind :meth:`commit_results`
        writes) are surfaced; other tracks are excluded.
        """
        if not enabled:
            return [], {}

        resource_where = {**where_filters, "track": "workspace"}
        resource_pool = store.resource_repo.list_resources(resource_where)
        resource_hits = store.resource_repo.vector_search_resources(
            query_vector, self.progressive_retrieve_config.resource.top_k, where=resource_where
        )
        return resource_hits, resource_pool

    def _materialize_hits(self, hits: Sequence[tuple[str, float]], pool: dict[str, Any]) -> list[dict[str, Any]]:
        """Expand ``(id, score)`` hits into scored, embedding-free dicts."""
        out = []
        for _id, score in hits:
            obj = pool.get(_id)
            if not obj:
                continue
            data = self._model_dump_without_embeddings(obj)
            data["score"] = float(score)
            out.append(data)
        return out

    async def commit_results(
        self,
        *,
        recall_files: list[dict[str, Any]] | None = None,
        resource: list[dict[str, Any]] | None = None,
        user: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist externally-prepared resources and recall files into the store.

        Takes items that were already preprocessed/synthesized off-service (see
        :mod:`memu.hosts.bridging.pipeline`), so it runs no ingest/preprocess/LLM
        steps — just create-or-update straight into storage:

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
        before the fresh record is created.
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

            caption_embedding = await _embed_one(embed_client, caption) if caption else None
            res = store.resource_repo.create_resource(
                url=url,
                local_path=url,
                caption=caption,
                embedding=caption_embedding,
                user_data=dict(user_scope or {}),
                # progressive_retrieve's resource layer filters on track="workspace";
                # commit is now the only resource writer, so tag it accordingly.
                track="workspace",
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
        and only take the new content. Segments are then reconciled per track.
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
                embedding = await _embed_one(embed_client, emb_text)
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
        embedding.
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
        vecs, _ = await embed_client.embed(to_add)
        for text, vec in zip(to_add, vecs, strict=True):
            store.recall_file_segment_repo.create_segment(
                recall_file_id=file.id, track=file_track, text=text, embedding=vec, user_data=dict(user_scope)
            )
