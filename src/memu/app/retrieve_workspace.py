from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel

from memu.vector import cosine_topk
from memu.workflow.step import WorkflowState, WorkflowStep

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from memu.app.settings import RetrieveWorkspaceConfig
    from memu.database.interfaces import Database


class RetrieveWorkspaceMixin:
    if TYPE_CHECKING:
        retrieve_workspace_config: RetrieveWorkspaceConfig
        _run_workflow: Callable[..., Awaitable[WorkflowState]]
        _get_database: Callable[[], Database]
        _get_step_embedding_client: Callable[[Mapping[str, Any] | None], Any]
        _model_dump_without_embeddings: Callable[[BaseModel], dict[str, Any]]
        user_model: type[BaseModel]

    async def retrieve_workspace(
        self,
        query: str,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Single-shot, LLM-free retrieval over the segment/file/resource layers.

        Mirrors the relation between :meth:`memorize` and ``memorize_workspace``:
        a simpler entry point built on the same store and workflow machinery. The
        query is embedded once and used to rank two layers by vector similarity —
        no intention routing, sufficiency checks, or summarization:

        * ``segments``: :class:`RecallFileSegment` slices ranked by embedding,
          ``file.top_k`` of them.
        * ``files``: the :class:`RecallFile`\\ s pointed to by those segments — not
          a ranked search, just a roll-up. Each file's score is the max score of
          the segments that point to it.
        * ``resources``: workspace-track resources ranked by embedding,
          ``resource.top_k`` of them.

        The entry layer is disabled here (its config is retained but ignored).
        Returns ``segments``, ``files``, and ``resources``.
        """
        if not query or not query.strip():
            raise ValueError("empty_query")
        store = self._get_database()
        where_filters = self._normalize_where(where)
        config = self.retrieve_workspace_config

        state: WorkflowState = {
            "query": query,
            "store": store,
            "where": where_filters,
            "retrieve_file": config.file.enabled,
            "retrieve_resource": config.resource.enabled,
        }

        result = await self._run_workflow("retrieve_workspace", state)
        response = cast(dict[str, Any] | None, result.get("response"))
        if response is None:
            msg = "Retrieve workspace workflow failed to produce a response"
            raise RuntimeError(msg)
        return response

    def _normalize_where(self, where: Mapping[str, Any] | None) -> dict[str, Any]:
        """Validate and clean the `where` scope filters against the configured user model."""
        if not where:
            return {}

        valid_fields = set(getattr(self.user_model, "model_fields", {}).keys())
        cleaned: dict[str, Any] = {}

        for raw_key, value in where.items():
            if value is None:
                continue
            field = raw_key.split("__", 1)[0]
            if field not in valid_fields:
                msg = f"Unknown filter field '{field}' for current user scope"
                raise ValueError(msg)
            cleaned[raw_key] = value

        return cleaned

    def _build_retrieve_workspace_workflow(self) -> list[WorkflowStep]:
        """The simple embedding-only workspace retrieval pipeline.

        A segment recall step ranks :class:`RecallFileSegment` slices by embedding;
        a file roll-up step gathers the files those segments point to; a resource
        recall step ranks workspace-track resources by embedding. A terminal step
        assembles the response. None of the routing/sufficiency machinery of
        ``retrieve_rag`` applies. The query vector is embedded by the first recall
        step and reused downstream.
        """
        steps = [
            WorkflowStep(
                step_id="recall_segments",
                role="recall_segments",
                handler=self._ws_recall_segments,
                requires={"retrieve_file", "query", "store", "where"},
                produces={"segment_hits", "segment_pool", "query_vector"},
                capabilities={"vector"},
                config={"embed_llm_profile": "embedding"},
            ),
            WorkflowStep(
                step_id="collect_files",
                role="collect_files",
                handler=self._ws_collect_files,
                requires={"retrieve_file", "segment_hits", "segment_pool", "store", "where"},
                produces={"file_hits", "file_pool", "file_resource_urls"},
                capabilities=set(),
            ),
            WorkflowStep(
                step_id="recall_resources",
                role="recall_resources",
                handler=self._ws_recall_resources,
                requires={"retrieve_resource", "query", "store", "where", "query_vector"},
                produces={"resource_hits", "resource_pool", "query_vector"},
                capabilities={"vector"},
                config={"embed_llm_profile": "embedding"},
            ),
            WorkflowStep(
                step_id="build_response",
                role="build_context",
                handler=self._ws_build_response,
                requires={
                    "segment_hits",
                    "segment_pool",
                    "file_hits",
                    "file_pool",
                    "file_resource_urls",
                    "resource_hits",
                    "resource_pool",
                },
                produces={"response"},
                capabilities=set(),
            ),
        ]
        return steps

    @staticmethod
    def _list_retrieve_workspace_initial_keys() -> set[str]:
        return {"query", "store", "where", "retrieve_file", "retrieve_resource"}

    async def _ws_query_vector(self, state: WorkflowState, step_context: Any) -> list[float]:
        """Embed the query once and cache it on the state for reuse across steps."""
        cached = state.get("query_vector")
        if cached is not None:
            return cast(list[float], cached)
        embed_client = self._get_step_embedding_client(step_context)
        qvec = (await embed_client.embed([state["query"]]))[0]
        state["query_vector"] = qvec
        return cast(list[float], qvec)

    async def _ws_recall_segments(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("retrieve_file"):
            state["segment_hits"] = []
            state["segment_pool"] = {}
            state.setdefault("query_vector", None)
            return state

        store = state["store"]
        # The segment repo has no vector search, so rank the stored segment
        # embeddings directly, mirroring how files used to be ranked. Optionally
        # scope to the requested tracks via the denormalized segment ``track``.
        segment_where = dict(state.get("where") or {})
        tracks = self.retrieve_workspace_config.file.tracks
        if tracks:
            segment_where["track__in"] = list(tracks)
        segment_pool = {seg.id: seg for seg in store.recall_file_segment_repo.list_segments(segment_where)}
        qvec = await self._ws_query_vector(state, step_context)
        state["segment_hits"] = cosine_topk(
            qvec,
            [(sid, seg.embedding) for sid, seg in segment_pool.items()],
            k=self.retrieve_workspace_config.file.top_k,
        )
        state["segment_pool"] = segment_pool
        return state

    async def _ws_collect_files(self, state: WorkflowState, _: Any) -> WorkflowState:
        """Roll the ranked segments up to their files (no ranked file search).

        Every file pointed to by a top segment is returned; a file's score is the
        max score across the segments that point to it.
        """
        segment_hits = state.get("segment_hits") or []
        segment_pool = state.get("segment_pool") or {}
        store = state["store"]
        where_filters = state.get("where") or {}
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
        state["file_hits"] = sorted(file_scores.items(), key=lambda kv: kv[1], reverse=True)
        state["file_pool"] = file_pool
        state["file_resource_urls"] = self._ws_collect_file_resource_urls(store, where_filters, file_pool)
        return state

    @staticmethod
    def _ws_collect_file_resource_urls(
        store: Database, where_filters: dict[str, Any], file_pool: dict[str, Any]
    ) -> dict[str, list[str]]:
        """Map each file id to the URLs of the resources linked to it.

        Resolves the ``RecallFileResource`` link table (file -> resource) and the
        resource records (resource -> url) within the current scope, surfacing url
        strings only — the raw resource/link ids are not exposed to callers.
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

    async def _ws_recall_resources(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("retrieve_resource"):
            state["resource_hits"] = []
            state["resource_pool"] = {}
            return state

        store = state["store"]
        # Workspace retrieval only surfaces resources ingested by
        # ``memorize_workspace`` (track="workspace"); other tracks are excluded.
        resource_where = {**(state.get("where") or {}), "track": "workspace"}
        resource_pool = store.resource_repo.list_resources(resource_where)
        qvec = await self._ws_query_vector(state, step_context)
        state["resource_hits"] = store.resource_repo.vector_search_resources(
            qvec, self.retrieve_workspace_config.resource.top_k, where=resource_where
        )
        state["resource_pool"] = resource_pool
        return state

    def _ws_build_response(self, state: WorkflowState, _: Any) -> WorkflowState:
        files = self._materialize_hits(state.get("file_hits", []), state.get("file_pool", {}))
        file_resource_urls = state.get("file_resource_urls", {})
        for file in files:
            file["resource_urls"] = file_resource_urls.get(file["id"], [])
        state["response"] = {
            "segments": self._materialize_hits(state.get("segment_hits", []), state.get("segment_pool", {})),
            "files": files,
            "resources": self._materialize_hits(state.get("resource_hits", []), state.get("resource_pool", {})),
        }
        return state

    def _materialize_hits(self, hits: Sequence[tuple[str, float]], pool: dict[str, Any]) -> list[dict[str, Any]]:
        out = []
        for _id, score in hits:
            obj = pool.get(_id)
            if not obj:
                continue
            data = self._model_dump_without_embeddings(obj)
            data["score"] = float(score)
            out.append(data)
        return out
