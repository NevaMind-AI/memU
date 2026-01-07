from __future__ import annotations

import json
import logging
import re
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel

from memu.database.inmemory.vector import cosine_topk
from memu.prompts.retrieve.llm_category_ranker import PROMPT as LLM_CATEGORY_RANKER_PROMPT
from memu.prompts.retrieve.llm_item_ranker import PROMPT as LLM_ITEM_RANKER_PROMPT
from memu.prompts.retrieve.llm_resource_ranker import PROMPT as LLM_RESOURCE_RANKER_PROMPT
from memu.prompts.retrieve.pre_retrieval_decision import SYSTEM_PROMPT as PRE_RETRIEVAL_SYSTEM_PROMPT
from memu.prompts.retrieve.pre_retrieval_decision import USER_PROMPT as PRE_RETRIEVAL_USER_PROMPT
from memu.workflow.step import WorkflowState, WorkflowStep

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from memu.app.service import Context
    from memu.app.settings import RetrieveConfig
    from memu.database.interfaces import Database


class RetrieveMixin:
    if TYPE_CHECKING:
        retrieve_config: RetrieveConfig
        _run_workflow: Callable[..., Awaitable[WorkflowState]]
        _get_context: Callable[[], Context]
        _get_database: Callable[[], Database]
        _ensure_categories_ready: Callable[[Context, Database], Awaitable[None]]
        _get_step_llm_client: Callable[[Mapping[str, Any] | None], Any]
        _get_step_embedding_client: Callable[[Mapping[str, Any] | None], Any]
        _get_llm_client: Callable[..., Any]
        _model_dump_without_embeddings: Callable[[BaseModel], dict[str, Any]]
        _extract_json_blob: Callable[[str], str]
        _escape_prompt_value: Callable[[str], str]
        user_model: type[BaseModel]

    async def retrieve(
        self,
        queries: list[dict[str, Any]],
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not queries:
            raise ValueError("empty_queries")
        ctx = self._get_context()
        store = self._get_database()
        original_query = self._extract_query_text(queries[-1])
        # await self._ensure_categories_ready(ctx, store)
        where_filters = self._normalize_where(where)

        context_queries_objs = queries[:-1] if len(queries) > 1 else []

        route_intention = self.retrieve_config.route_intention
        retrieve_category = self.retrieve_config.category.enabled
        retrieve_item = self.retrieve_config.item.enabled
        retrieve_resource = self.retrieve_config.resource.enabled
        sufficiency_check = self.retrieve_config.sufficiency_check

        workflow_name = "retrieve_llm" if self.retrieve_config.method == "llm" else "retrieve_rag"

        state: WorkflowState = {
            "method": self.retrieve_config.method,
            "original_query": original_query,
            "context_queries": context_queries_objs,
            "route_intention": route_intention,
            "skip_rewrite": len(queries) == 1,
            "retrieve_category": retrieve_category,
            "retrieve_item": retrieve_item,
            "retrieve_resource": retrieve_resource,
            "sufficiency_check": sufficiency_check,
            "ctx": ctx,
            "store": store,
            "where": where_filters,
        }

        result = await self._run_workflow(workflow_name, state)
        response = cast(dict[str, Any] | None, result.get("response"))
        if response is None:
            msg = "Retrieve workflow failed to produce a response"
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

    def _build_rag_retrieve_workflow(self) -> list[WorkflowStep]:
        steps = [
            WorkflowStep(
                step_id="route_intention",
                role="route_intention",
                handler=self._rag_route_intention,
                requires={"route_intention", "original_query", "context_queries", "skip_rewrite"},
                produces={"needs_retrieval", "rewritten_query", "active_query", "next_step_query"},
                capabilities={"llm"},
                config={"chat_llm_profile": self.retrieve_config.sufficiency_check_llm_profile},
            ),
            WorkflowStep(
                step_id="route_category",
                role="route_category",
                handler=self._rag_route_category,
                requires={"retrieve_category", "needs_retrieval", "active_query", "ctx", "store", "where"},
                produces={"category_hits", "category_summary_lookup", "query_vector"},
                capabilities={"vector"},
                config={"embed_llm_profile": "embedding"},
            ),
            WorkflowStep(
                step_id="sufficiency_after_category",
                role="sufficiency_check",
                handler=self._rag_category_sufficiency,
                requires={
                    "retrieve_category",
                    "needs_retrieval",
                    "active_query",
                    "context_queries",
                    "category_hits",
                    "ctx",
                    "store",
                    "where",
                },
                produces={"next_step_query", "proceed_to_items", "query_vector"},
                capabilities={"llm"},
                config={
                    "chat_llm_profile": self.retrieve_config.sufficiency_check_llm_profile,
                    "embed_llm_profile": "embedding",
                },
            ),
            WorkflowStep(
                step_id="recall_items",
                role="recall_items",
                handler=self._rag_recall_items,
                requires={
                    "needs_retrieval",
                    "proceed_to_items",
                    "ctx",
                    "store",
                    "where",
                    "active_query",
                    "query_vector",
                },
                produces={"item_hits", "query_vector"},
                capabilities={"vector"},
                config={"embed_llm_profile": "embedding"},
            ),
            WorkflowStep(
                step_id="sufficiency_after_items",
                role="sufficiency_check",
                handler=self._rag_item_sufficiency,
                requires={
                    "needs_retrieval",
                    "active_query",
                    "context_queries",
                    "item_hits",
                    "ctx",
                    "store",
                    "where",
                },
                produces={"next_step_query", "proceed_to_resources", "query_vector"},
                capabilities={"llm"},
                config={
                    "chat_llm_profile": self.retrieve_config.sufficiency_check_llm_profile,
                    "embed_llm_profile": "embedding",
                },
            ),
            WorkflowStep(
                step_id="recall_resources",
                role="recall_resources",
                handler=self._rag_recall_resources,
                requires={
                    "needs_retrieval",
                    "proceed_to_resources",
                    "ctx",
                    "store",
                    "where",
                    "active_query",
                    "query_vector",
                },
                produces={"resource_hits", "query_vector"},
                capabilities={"vector"},
                config={"embed_llm_profile": "embedding"},
            ),
            WorkflowStep(
                step_id="build_context",
                role="build_context",
                handler=self._rag_build_context,
                requires={"needs_retrieval", "original_query", "rewritten_query", "ctx", "store", "where"},
                produces={"response"},
                capabilities=set(),
            ),
        ]
        return steps

    def _list_retrieve_initial_keys(self) -> set[str]:
        return {
            "method",
            "original_query",
            "context_queries",
            "route_intention",
            "skip_rewrite",
            "retrieve_category",
            "retrieve_item",
            "retrieve_resource",
            "sufficiency_check",
            "ctx",
            "store",
            "where",
        }

    async def _rag_route_intention(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("route_intention"):
            state.update({
                "needs_retrieval": True,
                "rewritten_query": state["original_query"],
                "active_query": state["original_query"],
                "next_step_query": None,
                "proceed_to_items": False,
                "proceed_to_resources": False,
            })
            return state

        llm_client = self._get_step_llm_client(step_context)
        needs_retrieval, rewritten_query = await self._decide_if_retrieval_needed(
            state["original_query"],
            state["context_queries"],
            retrieved_content=None,
            llm_client=llm_client,
        )
        if state.get("skip_rewrite"):
            rewritten_query = state["original_query"]

        state.update({
            "needs_retrieval": needs_retrieval,
            "rewritten_query": rewritten_query,
            "active_query": rewritten_query,
            "next_step_query": None,
            "proceed_to_items": False,
            "proceed_to_resources": False,
        })
        return state

    async def _rag_route_category(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("retrieve_category") or not state.get("needs_retrieval"):
            state["category_hits"] = []
            state["category_summary_lookup"] = {}
            state["query_vector"] = None
            return state

        embed_client = self._get_step_embedding_client(step_context)
        store = state["store"]
        where_filters = state.get("where") or {}
        category_pool = store.memory_category_repo.list_categories(where_filters)
        qvec = (await embed_client.embed([state["active_query"]]))[0]
        hits, summary_lookup = await self._rank_categories_by_summary(
            qvec,
            self.retrieve_config.category.top_k,
            state["ctx"],
            store,
            embed_client=embed_client,
            categories=category_pool,
        )
        state.update({
            "query_vector": qvec,
            "category_hits": hits,
            "category_summary_lookup": summary_lookup,
            "category_pool": category_pool,
        })
        return state

    async def _rag_category_sufficiency(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("needs_retrieval"):
            state["proceed_to_items"] = False
            return state
        if not state.get("retrieve_category") or not state.get("sufficiency_check"):
            state["proceed_to_items"] = True
            return state

        retrieved_content = ""
        store = state["store"]
        where_filters = state.get("where") or {}
        category_pool = state.get("category_pool") or store.memory_category_repo.list_categories(where_filters)
        hits = state.get("category_hits") or []
        if hits:
            retrieved_content = self._format_category_content(
                hits,
                state.get("category_summary_lookup", {}),
                store,
                categories=category_pool,
            )

        llm_client = self._get_step_llm_client(step_context)
        needs_more, rewritten_query = await self._decide_if_retrieval_needed(
            state["active_query"],
            state["context_queries"],
            retrieved_content=retrieved_content or "No content retrieved yet.",
            llm_client=llm_client,
        )
        state["next_step_query"] = rewritten_query
        state["active_query"] = rewritten_query
        state["proceed_to_items"] = needs_more
        if needs_more:
            embed_client = self._get_step_embedding_client(step_context)
            state["query_vector"] = (await embed_client.embed([state["active_query"]]))[0]
        return state

    async def _rag_recall_items(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("retrieve_item") or not state.get("needs_retrieval") or not state.get("proceed_to_items"):
            state["item_hits"] = []
            return state

        store = state["store"]
        where_filters = state.get("where") or {}
        items_pool = store.memory_item_repo.list_items(where_filters)
        qvec = state.get("query_vector")
        if qvec is None:
            embed_client = self._get_step_embedding_client(step_context)
            qvec = (await embed_client.embed([state["active_query"]]))[0]
            state["query_vector"] = qvec
        state["item_hits"] = store.memory_item_repo.vector_search_items(
            qvec,
            self.retrieve_config.item.top_k,
            where=where_filters,
        )
        state["item_pool"] = items_pool
        return state

    async def _rag_item_sufficiency(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("needs_retrieval"):
            state["proceed_to_resources"] = False
            return state
        if not state.get("retrieve_item") or not state.get("sufficiency_check"):
            state["proceed_to_resources"] = True
            return state

        store = state["store"]
        where_filters = state.get("where") or {}
        items_pool = state.get("item_pool") or store.memory_item_repo.list_items(where_filters)
        retrieved_content = ""
        hits = state.get("item_hits") or []
        if hits:
            retrieved_content = self._format_item_content(hits, store, items=items_pool)

        llm_client = self._get_step_llm_client(step_context)
        needs_more, rewritten_query = await self._decide_if_retrieval_needed(
            state["active_query"],
            state["context_queries"],
            retrieved_content=retrieved_content or "No content retrieved yet.",
            llm_client=llm_client,
        )
        state["next_step_query"] = rewritten_query
        state["active_query"] = rewritten_query
        state["proceed_to_resources"] = needs_more
        if needs_more:
            embed_client = self._get_step_embedding_client(step_context)
            state["query_vector"] = (await embed_client.embed([state["active_query"]]))[0]
        return state

    async def _rag_recall_resources(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if (
            not state.get("needs_retrieval")
            or not state.get("retrieve_resource")
            or not state.get("proceed_to_resources")
        ):
            state["resource_hits"] = []
            return state

        store = state["store"]
        where_filters = state.get("where") or {}
        resource_pool = store.resource_repo.list_resources(where_filters)
        state["resource_pool"] = resource_pool
        corpus = self._resource_caption_corpus(store, resources=resource_pool)
        if not corpus:
            state["resource_hits"] = []
            return state

        qvec = state.get("query_vector")
        if qvec is None:
            embed_client = self._get_step_embedding_client(step_context)
            qvec = (await embed_client.embed([state["active_query"]]))[0]
            state["query_vector"] = qvec
        state["resource_hits"] = cosine_topk(qvec, corpus, k=self.retrieve_config.resource.top_k)
        return state

    def _rag_build_context(self, state: WorkflowState, _: Any) -> WorkflowState:
        response = {
            "needs_retrieval": bool(state.get("needs_retrieval")),
            "original_query": state["original_query"],
            "rewritten_query": state.get("rewritten_query", state["original_query"]),
            "next_step_query": state.get("next_step_query"),
            "categories": [],
            "items": [],
            "resources": [],
        }
        if state.get("needs_retrieval"):
            store = state["store"]
            where_filters = state.get("where") or {}
            categories_pool = state.get("category_pool") or store.memory_category_repo.list_categories(where_filters)
            items_pool = state.get("item_pool") or store.memory_item_repo.list_items(where_filters)
            resources_pool = state.get("resource_pool") or store.resource_repo.list_resources(where_filters)
            response["categories"] = self._materialize_hits(
                state.get("category_hits", []),
                categories_pool,
            )
            response["items"] = self._materialize_hits(state.get("item_hits", []), items_pool)
            response["resources"] = self._materialize_hits(
                state.get("resource_hits", []),
                resources_pool,
            )
        state["response"] = response
        return state

    def _build_llm_retrieve_workflow(self) -> list[WorkflowStep]:
        steps = [
            WorkflowStep(
                step_id="route_intention",
                role="route_intention",
                handler=self._llm_route_intention,
                requires={"original_query", "context_queries", "skip_rewrite"},
                produces={"needs_retrieval", "rewritten_query", "active_query", "next_step_query"},
                capabilities={"llm"},
                config={"llm_profile": self.retrieve_config.sufficiency_check_llm_profile},
            ),
            WorkflowStep(
                step_id="route_category",
                role="route_category",
                handler=self._llm_route_category,
                requires={"needs_retrieval", "active_query", "ctx", "store", "where"},
                produces={"category_hits"},
                capabilities={"llm"},
                config={"llm_profile": self.retrieve_config.llm_ranking_llm_profile},
            ),
            WorkflowStep(
                step_id="sufficiency_after_category",
                role="sufficiency_check",
                handler=self._llm_category_sufficiency,
                requires={"needs_retrieval", "active_query", "context_queries", "category_hits"},
                produces={"next_step_query", "proceed_to_items"},
                capabilities={"llm"},
                config={"llm_profile": self.retrieve_config.sufficiency_check_llm_profile},
            ),
            WorkflowStep(
                step_id="recall_items",
                role="recall_items",
                handler=self._llm_recall_items,
                requires={
                    "needs_retrieval",
                    "proceed_to_items",
                    "ctx",
                    "store",
                    "where",
                    "active_query",
                    "category_hits",
                },
                produces={"item_hits"},
                capabilities={"llm"},
                config={"llm_profile": self.retrieve_config.llm_ranking_llm_profile},
            ),
            WorkflowStep(
                step_id="sufficiency_after_items",
                role="sufficiency_check",
                handler=self._llm_item_sufficiency,
                requires={"needs_retrieval", "active_query", "context_queries", "item_hits"},
                produces={"next_step_query", "proceed_to_resources"},
                capabilities={"llm"},
                config={"llm_profile": self.retrieve_config.sufficiency_check_llm_profile},
            ),
            WorkflowStep(
                step_id="recall_resources",
                role="recall_resources",
                handler=self._llm_recall_resources,
                requires={
                    "needs_retrieval",
                    "proceed_to_resources",
                    "active_query",
                    "ctx",
                    "store",
                    "where",
                    "item_hits",
                    "category_hits",
                },
                produces={"resource_hits"},
                capabilities={"llm"},
                config={"llm_profile": self.retrieve_config.llm_ranking_llm_profile},
            ),
            WorkflowStep(
                step_id="build_context",
                role="build_context",
                handler=self._llm_build_context,
                requires={"needs_retrieval", "original_query", "rewritten_query"},
                produces={"response"},
                capabilities=set(),
            ),
        ]
        return steps

    async def _llm_route_intention(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("route_intention"):
            state.update({
                "needs_retrieval": True,
                "rewritten_query": state["original_query"],
                "active_query": state["original_query"],
                "next_step_query": None,
                "proceed_to_items": False,
                "proceed_to_resources": False,
            })
            return state

        llm_client = self._get_step_llm_client(step_context)
        needs_retrieval, rewritten_query = await self._decide_if_retrieval_needed(
            state["original_query"],
            state["context_queries"],
            retrieved_content=None,
            llm_client=llm_client,
        )
        if state.get("skip_rewrite"):
            rewritten_query = state["original_query"]

        state.update({
            "needs_retrieval": needs_retrieval,
            "rewritten_query": rewritten_query,
            "active_query": rewritten_query,
            "next_step_query": None,
            "proceed_to_items": False,
            "proceed_to_resources": False,
        })
        return state

    async def _llm_route_category(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("needs_retrieval"):
            state["category_hits"] = []
            return state
        llm_client = self._get_step_llm_client(step_context)
        store = state["store"]
        where_filters = state.get("where") or {}
        category_pool = store.memory_category_repo.list_categories(where_filters)
        hits = await self._llm_rank_categories(
            state["active_query"],
            self.retrieve_config.category.top_k,
            state["ctx"],
            store,
            llm_client=llm_client,
            categories=category_pool,
        )
        state["category_hits"] = hits
        state["category_pool"] = category_pool
        return state

    async def _llm_category_sufficiency(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("needs_retrieval"):
            state["proceed_to_items"] = False
            return state
        if not state.get("retrieve_category") or not state.get("sufficiency_check"):
            state["proceed_to_items"] = True
            return state

        retrieved_content = ""
        hits = state.get("category_hits") or []
        if hits:
            retrieved_content = self._format_llm_category_content(hits)

        llm_client = self._get_step_llm_client(step_context)
        needs_more, rewritten_query = await self._decide_if_retrieval_needed(
            state["active_query"],
            state["context_queries"],
            retrieved_content=retrieved_content or "No content retrieved yet.",
            llm_client=llm_client,
        )
        state["next_step_query"] = rewritten_query
        state["active_query"] = rewritten_query
        state["proceed_to_items"] = needs_more
        return state

    async def _llm_recall_items(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("needs_retrieval") or not state.get("proceed_to_items"):
            state["item_hits"] = []
            return state

        where_filters = state.get("where") or {}
        category_ids = [cat["id"] for cat in state.get("category_hits", [])]
        llm_client = self._get_step_llm_client(step_context)
        store = state["store"]
        items_pool = store.memory_item_repo.list_items(where_filters)
        relations = store.category_item_repo.list_relations(where_filters)
        category_pool = state.get("category_pool") or store.memory_category_repo.list_categories(where_filters)
        state["item_hits"] = await self._llm_rank_items(
            state["active_query"],
            self.retrieve_config.item.top_k,
            category_ids,
            state.get("category_hits", []),
            state["ctx"],
            store,
            llm_client=llm_client,
            categories=category_pool,
            items=items_pool,
            relations=relations,
        )
        state["item_pool"] = items_pool
        state["relation_pool"] = relations
        return state

    async def _llm_item_sufficiency(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("needs_retrieval"):
            state["proceed_to_resources"] = False
            return state
        if not state.get("retrieve_item") or not state.get("sufficiency_check"):
            state["proceed_to_resources"] = True
            return state

        retrieved_content = ""
        hits = state.get("item_hits") or []
        if hits:
            retrieved_content = self._format_llm_item_content(hits)

        llm_client = self._get_step_llm_client(step_context)
        needs_more, rewritten_query = await self._decide_if_retrieval_needed(
            state["active_query"],
            state["context_queries"],
            retrieved_content=retrieved_content or "No content retrieved yet.",
            llm_client=llm_client,
        )
        state["next_step_query"] = rewritten_query
        state["active_query"] = rewritten_query
        state["proceed_to_resources"] = needs_more
        return state

    async def _llm_recall_resources(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("needs_retrieval") or not state.get("proceed_to_resources"):
            state["resource_hits"] = []
            return state

        llm_client = self._get_step_llm_client(step_context)
        store = state["store"]
        where_filters = state.get("where") or {}
        resource_pool = store.resource_repo.list_resources(where_filters)
        items_pool = state.get("item_pool") or store.memory_item_repo.list_items(where_filters)
        state["resource_hits"] = await self._llm_rank_resources(
            state["active_query"],
            self.retrieve_config.resource.top_k,
            state.get("category_hits", []),
            state.get("item_hits", []),
            state["ctx"],
            store,
            llm_client=llm_client,
            items=items_pool,
            resources=resource_pool,
        )
        state["resource_pool"] = resource_pool
        return state

    def _llm_build_context(self, state: WorkflowState, _: Any) -> WorkflowState:
        response = {
            "needs_retrieval": bool(state.get("needs_retrieval")),
            "original_query": state["original_query"],
            "rewritten_query": state.get("rewritten_query", state["original_query"]),
            "next_step_query": state.get("next_step_query"),
            "categories": [],
            "items": [],
            "resources": [],
        }
        if state.get("needs_retrieval"):
            response["categories"] = list(state.get("category_hits") or [])
            response["items"] = list(state.get("item_hits") or [])
            response["resources"] = list(state.get("resource_hits") or [])
        state["response"] = response
        return state

    async def _rank_categories_by_summary(
        self,
        query_vec: list[float],
        top_k: int,
        ctx: Context,
        store: Database,
        embed_client: Any | None = None,
        categories: Mapping[str, Any] | None = None,
    ) -> tuple[list[tuple[str, float]], dict[str, str]]:
        category_pool = categories if categories is not None else store.memory_category_repo.categories
        entries = [(cid, cat.summary) for cid, cat in category_pool.items() if cat.summary]
        if not entries:
            return [], {}
        summary_texts = [summary for _, summary in entries]
        client = embed_client or self._get_llm_client()
        summary_embeddings = await client.embed(summary_texts)
        corpus = [(cid, emb) for (cid, _), emb in zip(entries, summary_embeddings, strict=True)]
        hits = cosine_topk(query_vec, corpus, k=top_k)
        summary_lookup = dict(entries)
        return hits, summary_lookup

    async def _decide_if_retrieval_needed(
        self,
        query: str,
        context_queries: list[dict[str, Any]] | None,
        retrieved_content: str | None = None,
        system_prompt: str | None = None,
        llm_client: Any | None = None,
    ) -> tuple[bool, str]:
        """
        Decide if the query requires memory retrieval (or MORE retrieval) and rewrite it with context.

        Args:
            query: The current query string
            context_queries: List of previous query objects with role and content
            retrieved_content: Content retrieved so far (if checking for sufficiency)
            system_prompt: Optional system prompt override

        Returns:
            Tuple of (needs_retrieval: bool, rewritten_query: str)
            - needs_retrieval: True if retrieval/more retrieval is needed
            - rewritten_query: The rewritten query for the next step
        """
        history_text = self._format_query_context(context_queries)
        content_text = retrieved_content or "No content retrieved yet."

        prompt = self.retrieve_config.sufficiency_check_prompt or PRE_RETRIEVAL_USER_PROMPT
        user_prompt = prompt.format(
            query=self._escape_prompt_value(query),
            conversation_history=self._escape_prompt_value(history_text),
            retrieved_content=self._escape_prompt_value(content_text),
        )

        sys_prompt = system_prompt or PRE_RETRIEVAL_SYSTEM_PROMPT
        client = llm_client or self._get_llm_client()
        response = await client.summarize(user_prompt, system_prompt=sys_prompt)
        decision = self._extract_decision(response)
        rewritten = self._extract_rewritten_query(response) or query

        return decision == "RETRIEVE", rewritten

    def _format_query_context(self, queries: list[dict[str, Any]] | None) -> str:
        """Format query context for prompts, including role information"""
        if not queries:
            return "No query context."

        lines = []
        for q in queries:
            if isinstance(q, str):
                # Backward compatibility
                lines.append(f"- {q}")
            elif isinstance(q, dict):
                role = q.get("role", "user")
                content = q.get("content")
                if isinstance(content, dict):
                    text = content.get("text", "")
                elif isinstance(content, str):
                    text = content
                else:
                    text = str(content)
                lines.append(f"- [{role}]: {text}")
            else:
                lines.append(f"- {q!s}")

        return "\n".join(lines)

    @staticmethod
    def _extract_query_text(query: dict[str, Any]) -> str:
        """
        Extract text content from query message structure.

        Args:
            query: Query in format {"role": "user", "content": {"text": "..."}}

        Returns:
            The extracted text string
        """
        if isinstance(query, str):
            # Backward compatibility: if it's already a string, return it
            return query

        if not isinstance(query, dict):
            raise TypeError("INVALID")

        content = query.get("content")
        if isinstance(content, dict):
            text = content.get("text", "")
            if not text:
                raise ValueError("EMPTY")
            return str(text)
        elif isinstance(content, str):
            # Also support {"role": "user", "content": "text"} format
            return content
        else:
            raise TypeError("INVALID")

    def _extract_decision(self, raw: str) -> str:
        """Extract RETRIEVE or NO_RETRIEVE decision from LLM response"""
        if not raw:
            return "RETRIEVE"  # Default to retrieve if uncertain

        match = re.search(r"<decision>(.*?)</decision>", raw, re.IGNORECASE | re.DOTALL)
        if match:
            decision = match.group(1).strip().upper()
            if "NO_RETRIEVE" in decision or "NO RETRIEVE" in decision:
                return "NO_RETRIEVE"
            if "RETRIEVE" in decision:
                return "RETRIEVE"

        upper = raw.strip().upper()
        if "NO_RETRIEVE" in upper or "NO RETRIEVE" in upper:
            return "NO_RETRIEVE"

        return "RETRIEVE"  # Default to retrieve

    def _extract_rewritten_query(self, raw: str) -> str | None:
        """Extract rewritten query from LLM response"""
        match = re.search(r"<rewritten_query>(.*?)</rewritten_query>", raw, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    async def _embedding_based_retrieve(
        self,
        query: str,
        top_k: int,
        context_queries: list[dict[str, Any]] | None,
        ctx: Context,
        store: Database,
        llm_client: Any | None = None,
        where: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Embedding-based retrieval with query rewriting and judging at each tier"""
        where_filters = self._normalize_where(where)
        category_pool = store.memory_category_repo.list_categories(where_filters)
        items_pool = store.memory_item_repo.list_items(where_filters)
        resource_pool = store.resource_repo.list_resources(where_filters)
        client = llm_client or self._get_llm_client()
        current_query = query
        qvec = (await client.embed([current_query]))[0]
        response: dict[str, Any] = {"resources": [], "items": [], "categories": [], "next_step_query": None}
        content_sections: list[str] = []

        # Tier 1: Categories
        cat_hits, summary_lookup = await self._rank_categories_by_summary(
            qvec,
            top_k,
            ctx,
            store,
            embed_client=client,
            categories=category_pool,
        )
        if cat_hits:
            response["categories"] = self._materialize_hits(cat_hits, category_pool)
            content_sections.append(
                self._format_category_content(cat_hits, summary_lookup, store, categories=category_pool)
            )

            needs_more, current_query = await self._decide_if_retrieval_needed(
                current_query,
                context_queries,
                retrieved_content="\n\n".join(content_sections),
                llm_client=client,
            )
            response["next_step_query"] = current_query
            if not needs_more:
                return response
            # Re-embed with rewritten query
            qvec = (await client.embed([current_query]))[0]

        # Tier 2: Items
        item_hits = store.memory_item_repo.vector_search_items(qvec, top_k, where=where_filters)
        if item_hits:
            response["items"] = self._materialize_hits(item_hits, items_pool)
            content_sections.append(self._format_item_content(item_hits, store, items=items_pool))

            needs_more, current_query = await self._decide_if_retrieval_needed(
                current_query,
                context_queries,
                retrieved_content="\n\n".join(content_sections),
                llm_client=client,
            )
            response["next_step_query"] = current_query
            if not needs_more:
                return response
            # Re-embed with rewritten query
            qvec = (await client.embed([current_query]))[0]

        # Tier 3: Resources
        resource_corpus = self._resource_caption_corpus(store, resources=resource_pool)
        if resource_corpus:
            res_hits = cosine_topk(qvec, resource_corpus, k=top_k)
            if res_hits:
                response["resources"] = self._materialize_hits(res_hits, resource_pool)
                content_sections.append(self._format_resource_content(res_hits, store, resources=resource_pool))

        return response

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

    def _format_category_content(
        self,
        hits: list[tuple[str, float]],
        summaries: dict[str, str],
        store: Database,
        categories: Mapping[str, Any] | None = None,
    ) -> str:
        category_pool = categories if categories is not None else store.memory_category_repo.categories
        lines = []
        for cid, score in hits:
            cat = category_pool.get(cid)
            if not cat:
                continue
            summary = summaries.get(cid) or cat.summary or ""
            lines.append(f"Category: {cat.name}\nSummary: {summary}\nScore: {score:.3f}")
        return "\n\n".join(lines).strip()

    def _format_item_content(
        self, hits: list[tuple[str, float]], store: Database, items: Mapping[str, Any] | None = None
    ) -> str:
        item_pool = items if items is not None else store.memory_item_repo.items
        lines = []
        for iid, score in hits:
            item = item_pool.get(iid)
            if not item:
                continue
            lines.append(f"Memory Item ({item.memory_type}): {item.summary}\nScore: {score:.3f}")
        return "\n\n".join(lines).strip()

    def _format_resource_content(
        self, hits: list[tuple[str, float]], store: Database, resources: Mapping[str, Any] | None = None
    ) -> str:
        resource_pool = resources if resources is not None else store.resource_repo.resources
        lines = []
        for rid, score in hits:
            res = resource_pool.get(rid)
            if not res:
                continue
            caption = res.caption or f"Resource {res.url}"
            lines.append(f"Resource: {caption}\nScore: {score:.3f}")
        return "\n\n".join(lines).strip()

    def _resource_caption_corpus(
        self, store: Database, resources: Mapping[str, Any] | None = None
    ) -> list[tuple[str, list[float]]]:
        resource_pool = resources if resources is not None else store.resource_repo.resources
        corpus: list[tuple[str, list[float]]] = []
        for rid, res in resource_pool.items():
            if res.embedding:
                corpus.append((rid, res.embedding))
        return corpus

    def _extract_judgement(self, raw: str) -> str:
        if not raw:
            return "MORE"
        match = re.search(r"<judgement>(.*?)</judgement>", raw, re.IGNORECASE | re.DOTALL)
        if match:
            token = match.group(1).strip().upper()
            if "ENOUGH" in token:
                return "ENOUGH"
            if "MORE" in token:
                return "MORE"
        upper = raw.strip().upper()
        if "ENOUGH" in upper:
            return "ENOUGH"
        return "MORE"

    async def _llm_based_retrieve(
        self,
        query: str,
        top_k: int,
        context_queries: list[dict[str, Any]] | None,
        ctx: Context,
        store: Database,
        llm_client: Any | None = None,
        where: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        LLM-based retrieval that uses language model to search and rank results
        in a hierarchical manner, with query rewriting and judging at each tier.

        Flow:
        1. Search categories with LLM, judge + rewrite query
        2. If needs more, search items from relevant categories, judge + rewrite
        3. If needs more, search resources related to context
        """
        where_filters = self._normalize_where(where)
        category_pool = store.memory_category_repo.list_categories(where_filters)
        items_pool = store.memory_item_repo.list_items(where_filters)
        relations = store.category_item_repo.list_relations(where_filters)
        resource_pool = store.resource_repo.list_resources(where_filters)
        current_query = query
        client = llm_client or self._get_llm_client()
        response: dict[str, Any] = {"resources": [], "items": [], "categories": [], "next_step_query": None}
        content_sections: list[str] = []

        # Tier 1: Search and rank categories
        category_hits = await self._llm_rank_categories(
            current_query,
            top_k,
            ctx,
            store,
            llm_client=client,
            categories=category_pool,
        )
        if category_hits:
            response["categories"] = category_hits
            content_sections.append(self._format_llm_category_content(category_hits))

            needs_more, current_query = await self._decide_if_retrieval_needed(
                current_query,
                context_queries,
                retrieved_content="\n\n".join(content_sections),
                llm_client=client,
            )
            response["next_step_query"] = current_query
            if not needs_more:
                return response

        # Tier 2: Search memory items from relevant categories
        relevant_category_ids = [cat["id"] for cat in category_hits]
        item_hits = await self._llm_rank_items(
            current_query,
            top_k,
            relevant_category_ids,
            category_hits,
            ctx,
            store,
            llm_client=client,
            categories=category_pool,
            items=items_pool,
            relations=relations,
        )
        if item_hits:
            response["items"] = item_hits
            content_sections.append(self._format_llm_item_content(item_hits))

            needs_more, current_query = await self._decide_if_retrieval_needed(
                current_query,
                context_queries,
                retrieved_content="\n\n".join(content_sections),
                llm_client=client,
            )
            response["next_step_query"] = current_query
            if not needs_more:
                return response

        # Tier 3: Search resources related to the context
        resource_hits = await self._llm_rank_resources(
            current_query,
            top_k,
            category_hits,
            item_hits,
            ctx,
            store,
            llm_client=client,
            items=items_pool,
            resources=resource_pool,
        )
        if resource_hits:
            response["resources"] = resource_hits
            content_sections.append(self._format_llm_resource_content(resource_hits))

        return response

    def _format_categories_for_llm(
        self,
        store: Database,
        category_ids: list[str] | None = None,
        categories: Mapping[str, Any] | None = None,
    ) -> str:
        """Format categories for LLM consumption"""
        categories_to_format = categories if categories is not None else store.memory_category_repo.categories
        if category_ids:
            categories_to_format = {cid: cat for cid, cat in categories_to_format.items() if cid in category_ids}

        if not categories_to_format:
            return "No categories available."

        lines = []
        for cid, cat in categories_to_format.items():
            lines.append(f"ID: {cid}")
            lines.append(f"Name: {cat.name}")
            if cat.description:
                lines.append(f"Description: {cat.description}")
            if cat.summary:
                lines.append(f"Summary: {cat.summary}")
            lines.append("---")

        return "\n".join(lines)

    def _format_items_for_llm(
        self,
        store: Database,
        category_ids: list[str] | None = None,
        items: Mapping[str, Any] | None = None,
        relations: Sequence[Any] | None = None,
    ) -> str:
        """Format memory items for LLM consumption, optionally filtered by category"""
        item_pool = items if items is not None else store.memory_item_repo.items
        relation_pool = relations if relations is not None else store.category_item_repo.relations
        items_to_format = []
        seen_item_ids = set()

        if category_ids:
            # Get items that belong to the specified categories
            for rel in relation_pool:
                if rel.category_id in category_ids:
                    item = item_pool.get(rel.item_id)
                    if item and item.id not in seen_item_ids:
                        items_to_format.append(item)
                        seen_item_ids.add(item.id)
        else:
            items_to_format = list(item_pool.values())

        if not items_to_format:
            return "No memory items available."

        lines = []
        for item in items_to_format:
            lines.append(f"ID: {item.id}")
            lines.append(f"Type: {item.memory_type}")
            lines.append(f"Summary: {item.summary}")
            lines.append("---")

        return "\n".join(lines)

    def _format_resources_for_llm(
        self,
        store: Database,
        item_ids: list[str] | None = None,
        items: Mapping[str, Any] | None = None,
        resources: Mapping[str, Any] | None = None,
    ) -> str:
        """Format resources for LLM consumption, optionally filtered by related items"""
        resource_pool = resources if resources is not None else store.resource_repo.resources
        item_pool = items if items is not None else store.memory_item_repo.items
        resources_to_format = []

        if item_ids:
            # Get resources that are related to the specified items
            resource_ids = {item_pool[iid].resource_id for iid in item_ids if iid in item_pool and iid is not None}
            resources_to_format = [
                resource_pool[rid] for rid in resource_ids if rid in resource_pool and rid is not None
            ]
        else:
            resources_to_format = list(resource_pool.values())

        if not resources_to_format:
            return "No resources available."

        lines = []
        for res in resources_to_format:
            lines.append(f"ID: {res.id}")
            lines.append(f"URL: {res.url}")
            lines.append(f"Modality: {res.modality}")
            if res.caption:
                lines.append(f"Caption: {res.caption}")
            lines.append("---")

        return "\n".join(lines)

    async def _llm_rank_categories(
        self,
        query: str,
        top_k: int,
        ctx: Context,
        store: Database,
        llm_client: Any | None = None,
        categories: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Use LLM to rank categories based on query relevance"""
        category_pool = categories if categories is not None else store.memory_category_repo.categories
        if not category_pool:
            return []

        categories_data = self._format_categories_for_llm(store, categories=category_pool)
        prompt = LLM_CATEGORY_RANKER_PROMPT.format(
            query=self._escape_prompt_value(query),
            top_k=top_k,
            categories_data=self._escape_prompt_value(categories_data),
        )

        client = llm_client or self._get_llm_client()
        llm_response = await client.summarize(prompt, system_prompt=None)
        return self._parse_llm_category_response(llm_response, store, categories=category_pool)

    async def _llm_rank_items(
        self,
        query: str,
        top_k: int,
        category_ids: list[str],
        category_hits: list[dict[str, Any]],
        ctx: Context,
        store: Database,
        llm_client: Any | None = None,
        categories: Mapping[str, Any] | None = None,
        items: Mapping[str, Any] | None = None,
        relations: Sequence[Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Use LLM to rank memory items from relevant categories"""
        if not category_ids:
            print("[LLM Rank Items] No category_ids provided")
            return []

        item_pool = items if items is not None else store.memory_item_repo.items
        items_data = self._format_items_for_llm(store, category_ids, items=item_pool, relations=relations)
        if items_data == "No memory items available.":
            return []

        # Format relevant categories for context
        relevant_categories_info = "\n".join([
            f"- {cat['name']}: {cat.get('summary', cat.get('description', ''))}" for cat in category_hits
        ])

        prompt = LLM_ITEM_RANKER_PROMPT.format(
            query=self._escape_prompt_value(query),
            top_k=top_k,
            relevant_categories=self._escape_prompt_value(relevant_categories_info),
            items_data=self._escape_prompt_value(items_data),
        )

        client = llm_client or self._get_llm_client()
        llm_response = await client.summarize(prompt, system_prompt=None)
        return self._parse_llm_item_response(llm_response, store, items=item_pool)

    async def _llm_rank_resources(
        self,
        query: str,
        top_k: int,
        category_hits: list[dict[str, Any]],
        item_hits: list[dict[str, Any]],
        ctx: Context,
        store: Database,
        llm_client: Any | None = None,
        items: Mapping[str, Any] | None = None,
        resources: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Use LLM to rank resources related to the context"""
        # Get item IDs to filter resources
        item_ids = [item["id"] for item in item_hits]
        if not item_ids:
            return []

        item_pool = items if items is not None else store.memory_item_repo.items
        resource_pool = resources if resources is not None else store.resource_repo.resources
        resources_data = self._format_resources_for_llm(store, item_ids, items=item_pool, resources=resource_pool)
        if resources_data == "No resources available.":
            return []

        # Build context info
        context_parts = []
        if category_hits:
            context_parts.append("Relevant Categories:")
            context_parts.extend([f"- {cat['name']}" for cat in category_hits])
        if item_hits:
            context_parts.append("\nRelevant Memory Items:")
            context_parts.extend([f"- {item.get('summary', '')[:100]}..." for item in item_hits[:3]])

        context_info = "\n".join(context_parts)
        prompt = LLM_RESOURCE_RANKER_PROMPT.format(
            query=self._escape_prompt_value(query),
            top_k=top_k,
            context_info=self._escape_prompt_value(context_info),
            resources_data=self._escape_prompt_value(resources_data),
        )

        client = llm_client or self._get_llm_client()
        llm_response = await client.summarize(prompt, system_prompt=None)
        return self._parse_llm_resource_response(llm_response, store, resources=resource_pool)

    def _parse_llm_category_response(
        self, raw_response: str, store: Database, categories: Mapping[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Parse LLM category ranking response"""
        category_pool = categories if categories is not None else store.memory_category_repo.categories
        results = []
        try:
            json_blob = self._extract_json_blob(raw_response)
            parsed = json.loads(json_blob)

            if "categories" in parsed and isinstance(parsed["categories"], list):
                category_ids = parsed["categories"]
                # Return categories in the order provided by LLM (already sorted by relevance)
                for cat_id in category_ids:
                    if isinstance(cat_id, str):
                        cat = category_pool.get(cat_id)
                        if cat:
                            cat_data = self._model_dump_without_embeddings(cat)
                            results.append(cat_data)
        except Exception as e:
            logger.warning(f"Failed to parse LLM category ranking response: {e}")

        return results

    def _parse_llm_item_response(
        self, raw_response: str, store: Database, items: Mapping[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Parse LLM item ranking response"""
        item_pool = items if items is not None else store.memory_item_repo.items
        results = []
        try:
            json_blob = self._extract_json_blob(raw_response)
            parsed = json.loads(json_blob)

            if "items" in parsed and isinstance(parsed["items"], list):
                item_ids = parsed["items"]
                # Return items in the order provided by LLM (already sorted by relevance)
                for item_id in item_ids:
                    if isinstance(item_id, str):
                        mem_item = item_pool.get(item_id)
                        if mem_item:
                            item_data = self._model_dump_without_embeddings(mem_item)
                            results.append(item_data)
        except Exception as e:
            logger.warning(f"Failed to parse LLM item ranking response: {e}")

        return results

    def _parse_llm_resource_response(
        self, raw_response: str, store: Database, resources: Mapping[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Parse LLM resource ranking response"""
        resource_pool = resources if resources is not None else store.resource_repo.resources
        results = []
        try:
            json_blob = self._extract_json_blob(raw_response)
            parsed = json.loads(json_blob)

            if "resources" in parsed and isinstance(parsed["resources"], list):
                resource_ids = parsed["resources"]
                # Return resources in the order provided by LLM (already sorted by relevance)
                for res_id in resource_ids:
                    if isinstance(res_id, str):
                        res = resource_pool.get(res_id)
                        if res:
                            res_data = self._model_dump_without_embeddings(res)
                            results.append(res_data)
        except Exception as e:
            logger.warning(f"Failed to parse LLM resource ranking response: {e}")

        return results

    def _format_llm_category_content(self, hits: list[dict[str, Any]]) -> str:
        """Format LLM-ranked category content for judger"""
        lines = []
        for cat in hits:
            summary = cat.get("summary", "") or cat.get("description", "")
            lines.append(f"Category: {cat['name']}\nSummary: {summary}")
        return "\n\n".join(lines).strip()

    def _format_llm_item_content(self, hits: list[dict[str, Any]]) -> str:
        """Format LLM-ranked item content for judger"""
        lines = []
        for item in hits:
            lines.append(f"Memory Item ({item['memory_type']}): {item['summary']}")
        return "\n\n".join(lines).strip()

    def _format_llm_resource_content(self, hits: list[dict[str, Any]]) -> str:
        """Format LLM-ranked resource content for judger"""
        lines = []
        for res in hits:
            caption = res.get("caption", "") or f"Resource {res['url']}"
            lines.append(f"Resource: {caption}")
        return "\n\n".join(lines).strip()
