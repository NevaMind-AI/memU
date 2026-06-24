from __future__ import annotations

import json
import logging
import re
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel

from memu.prompts.retrieve.llm_category_ranker import PROMPT as LLM_CATEGORY_RANKER_PROMPT
from memu.prompts.retrieve.llm_item_ranker import PROMPT as LLM_ITEM_RANKER_PROMPT
from memu.prompts.retrieve.llm_resource_ranker import PROMPT as LLM_RESOURCE_RANKER_PROMPT
from memu.prompts.retrieve.pre_retrieval_decision import SYSTEM_PROMPT as PRE_RETRIEVAL_SYSTEM_PROMPT
from memu.prompts.retrieve.pre_retrieval_decision import USER_PROMPT as PRE_RETRIEVAL_USER_PROMPT
from memu.workflow.step import WorkflowState, WorkflowStep

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from memu.app.service import Context
    from memu.app.settings import MemorizeConfig, RetrieveConfig
    from memu.database.interfaces import Database


class RetrieveMixin:
    if TYPE_CHECKING:
        retrieve_config: RetrieveConfig
        memorize_config: MemorizeConfig
        _run_workflow: Callable[..., Awaitable[WorkflowState]]
        _get_context: Callable[[], Context]
        _get_database: Callable[[], Database]
        _get_step_llm_client: Callable[[Mapping[str, Any] | None], Any]
        _get_step_embedding_client: Callable[[Mapping[str, Any] | None], Any]
        _get_llm_client: Callable[..., Any]
        _get_embedding_client: Callable[..., Any]
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
                step_id="recall_lanes",
                role="recall_lanes",
                handler=self._rag_recall_lanes,
                requires={
                    "retrieve_category",
                    "retrieve_item",
                    "needs_retrieval",
                    "active_query",
                    "ctx",
                    "store",
                    "where",
                },
                produces={"lane_hits", "query_vector"},
                capabilities={"vector"},
                config={"embed_llm_profile": "embedding"},
            ),
            WorkflowStep(
                step_id="recall_resources",
                role="recall_resources",
                handler=self._rag_recall_resources,
                requires={
                    "needs_retrieval",
                    "retrieve_resource",
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
                requires={
                    "needs_retrieval",
                    "original_query",
                    "rewritten_query",
                    "lane_hits",
                    "resource_hits",
                    "ctx",
                    "store",
                    "where",
                },
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

    def _retrievable_lanes(self) -> list[str]:
        """Enabled lanes that participate in retrieval, in canonical order."""
        from memu.database.models import RETRIEVAL_LANES

        enabled = self.memorize_config.enabled_lanes
        return [lane for lane in RETRIEVAL_LANES if lane in enabled]

    async def _rag_recall_lanes(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        """Single-pass per-lane recall: coarse lane docs + entries for each lane."""
        lane_hits: dict[str, dict[str, list[tuple[str, float]]]] = {}
        if not state.get("needs_retrieval"):
            state["lane_hits"] = lane_hits
            state["query_vector"] = None
            return state

        store = state["store"]
        where_filters = state.get("where") or {}
        embed_client = self._get_step_embedding_client(step_context)
        qvec = (await embed_client.embed([state["active_query"]]))[0]
        state["query_vector"] = qvec

        retrieve_docs = bool(state.get("retrieve_category"))
        retrieve_entries = bool(state.get("retrieve_item"))
        for lane in self._retrievable_lanes():
            doc_hits: list[tuple[str, float]] = []
            entry_hits: list[tuple[str, float]] = []
            if retrieve_docs:
                doc_hits = store.resource_repo.vector_search_resources(
                    qvec, self.retrieve_config.category.top_k, where=where_filters, lane=lane
                )
            if retrieve_entries:
                entry_hits = store.entry_repo.vector_search_entries(
                    qvec,
                    self.retrieve_config.item.top_k,
                    where=where_filters,
                    lane=lane,
                    ranking=self.retrieve_config.item.ranking,
                    recency_decay_days=self.retrieve_config.item.recency_decay_days,
                )
            lane_hits[lane] = {"docs": doc_hits, "entries": entry_hits}
        state["lane_hits"] = lane_hits
        return state

    async def _rag_recall_resources(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("needs_retrieval") or not state.get("retrieve_resource"):
            state["resource_hits"] = []
            return state

        store = state["store"]
        where_filters = state.get("where") or {}
        qvec = state.get("query_vector")
        if qvec is None:
            embed_client = self._get_step_embedding_client(step_context)
            qvec = (await embed_client.embed([state["active_query"]]))[0]
            state["query_vector"] = qvec
        state["resource_hits"] = store.resource_repo.vector_search_resources(
            qvec, self.retrieve_config.resource.top_k, where=where_filters, lane="source"
        )
        return state

    def _rag_build_context(self, state: WorkflowState, _: Any) -> WorkflowState:
        response: dict[str, Any] = {
            "needs_retrieval": bool(state.get("needs_retrieval")),
            "original_query": state["original_query"],
            "rewritten_query": state.get("rewritten_query", state["original_query"]),
            "next_step_query": state.get("next_step_query"),
            "lanes": {},
            "categories": [],
            "items": [],
            "resources": [],
        }
        if state.get("needs_retrieval"):
            store = state["store"]
            where_filters = state.get("where") or {}
            lane_hits: dict[str, dict[str, list[tuple[str, float]]]] = state.get("lane_hits", {})
            lanes_out: dict[str, dict[str, Any]] = {}
            for lane, hits in lane_hits.items():
                docs_pool = store.resource_repo.list_resources(where_filters, lane=lane)
                entries_pool = store.entry_repo.list_entries(where_filters, lane=lane)
                lanes_out[lane] = {
                    "categories": self._materialize_hits(hits.get("docs", []), docs_pool),
                    "items": self._materialize_hits(hits.get("entries", []), entries_pool),
                }
            resources_pool = store.resource_repo.list_resources(where_filters, lane="source")
            response["lanes"] = lanes_out
            response["resources"] = self._materialize_hits(state.get("resource_hits", []), resources_pool)
            # Backward-compatible top-level view: the memory lane.
            memory_out = lanes_out.get("memory", {})
            response["categories"] = memory_out.get("categories", [])
            response["items"] = memory_out.get("items", [])
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
                step_id="recall_lanes",
                role="recall_lanes",
                handler=self._llm_recall_lanes,
                requires={"needs_retrieval", "active_query", "ctx", "store", "where"},
                produces={"lane_hits"},
                capabilities={"llm"},
                config={"llm_profile": self.retrieve_config.llm_ranking_llm_profile},
            ),
            WorkflowStep(
                step_id="recall_resources",
                role="recall_resources",
                handler=self._llm_recall_resources,
                requires={
                    "needs_retrieval",
                    "retrieve_resource",
                    "active_query",
                    "ctx",
                    "store",
                    "where",
                    "lane_hits",
                },
                produces={"resource_hits"},
                capabilities={"llm"},
                config={"llm_profile": self.retrieve_config.llm_ranking_llm_profile},
            ),
            WorkflowStep(
                step_id="build_context",
                role="build_context",
                handler=self._llm_build_context,
                requires={"needs_retrieval", "original_query", "rewritten_query", "lane_hits", "resource_hits"},
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

    async def _llm_recall_lanes(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        """Single-pass per-lane LLM recall: rank coarse lane docs + entries per lane."""
        lane_hits: dict[str, dict[str, list[dict[str, Any]]]] = {}
        if not state.get("needs_retrieval"):
            state["lane_hits"] = lane_hits
            return state

        llm_client = self._get_step_llm_client(step_context)
        store = state["store"]
        where_filters = state.get("where") or {}
        active_query = state["active_query"]

        for lane in self._retrievable_lanes():
            docs_pool = store.resource_repo.list_resources(where_filters, lane=lane)
            doc_hits = await self._llm_rank_categories(
                active_query,
                self.retrieve_config.category.top_k,
                state["ctx"],
                store,
                llm_client=llm_client,
                categories=docs_pool,
            )
            entries_pool = store.entry_repo.list_entries(where_filters, lane=lane)
            entry_hits = await self._llm_rank_entries(
                active_query,
                self.retrieve_config.item.top_k,
                doc_hits,
                state["ctx"],
                store,
                llm_client=llm_client,
                entries=entries_pool,
            )
            lane_hits[lane] = {"categories": doc_hits, "items": entry_hits}
        state["lane_hits"] = lane_hits
        return state

    async def _llm_recall_resources(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("needs_retrieval") or not state.get("retrieve_resource"):
            state["resource_hits"] = []
            return state

        llm_client = self._get_step_llm_client(step_context)
        store = state["store"]
        where_filters = state.get("where") or {}
        resource_pool = store.resource_repo.list_resources(where_filters, lane="source")
        lane_hits: dict[str, dict[str, list[dict[str, Any]]]] = state.get("lane_hits", {})
        # Aggregate entry/doc hits across lanes for resource ranking context.
        all_item_hits: list[dict[str, Any]] = []
        all_category_hits: list[dict[str, Any]] = []
        for hits in lane_hits.values():
            all_item_hits.extend(hits.get("items", []))
            all_category_hits.extend(hits.get("categories", []))
        items_pool = store.entry_repo.list_entries(where_filters)
        state["resource_hits"] = await self._llm_rank_resources(
            state["active_query"],
            self.retrieve_config.resource.top_k,
            all_category_hits,
            all_item_hits,
            state["ctx"],
            store,
            llm_client=llm_client,
            items=items_pool,
            resources=resource_pool,
        )
        return state

    def _llm_build_context(self, state: WorkflowState, _: Any) -> WorkflowState:
        response: dict[str, Any] = {
            "needs_retrieval": bool(state.get("needs_retrieval")),
            "original_query": state["original_query"],
            "rewritten_query": state.get("rewritten_query", state["original_query"]),
            "next_step_query": state.get("next_step_query"),
            "lanes": {},
            "categories": [],
            "items": [],
            "resources": [],
        }
        if state.get("needs_retrieval"):
            lane_hits: dict[str, dict[str, list[dict[str, Any]]]] = state.get("lane_hits", {})
            response["lanes"] = lane_hits
            response["resources"] = list(state.get("resource_hits") or [])
            memory_out = lane_hits.get("memory", {})
            response["categories"] = list(memory_out.get("categories", []))
            response["items"] = list(memory_out.get("items", []))
        state["response"] = response
        return state

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
        response = await client.chat(user_prompt, system_prompt=sys_prompt)
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

    def _format_categories_for_llm(
        self,
        store: Database,
        category_ids: list[str] | None = None,
        categories: Mapping[str, Any] | None = None,
    ) -> str:
        """Format categories for LLM consumption"""
        categories_to_format = (
            categories if categories is not None else store.resource_repo.list_resources(lane="memory")
        )
        if category_ids:
            categories_to_format = {cid: cat for cid, cat in categories_to_format.items() if cid in category_ids}

        if not categories_to_format:
            return "No categories available."

        lines = []
        for cid, cat in categories_to_format.items():
            lines.append(f"ID: {cid}")
            lines.append(f"Name: {cat.title}")
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
        item_pool = items if items is not None else store.entry_repo.list_entries(lane="memory")
        relation_pool = relations if relations is not None else store.resource_entry_repo.relations
        items_to_format = []
        seen_item_ids = set()

        if category_ids:
            # Get items that belong to the specified categories
            for rel in relation_pool:
                if rel.resource_id in category_ids:
                    item = item_pool.get(rel.entry_id)
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
            lines.append(f"Type: {item.entry_type}")
            lines.append(f"Summary: {item.text}")
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
        item_pool = items if items is not None else store.entry_repo.list_entries(lane="memory")
        resources_to_format = []

        if item_ids:
            # Get resources that are related to the specified items
            resource_ids = {item_pool[iid].source_id for iid in item_ids if iid in item_pool and iid is not None}
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
            if res.summary:
                lines.append(f"Caption: {res.summary}")
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
        category_pool = categories if categories is not None else store.resource_repo.list_resources(lane="memory")
        if not category_pool:
            return []

        categories_data = self._format_categories_for_llm(store, categories=category_pool)
        prompt = LLM_CATEGORY_RANKER_PROMPT.format(
            query=self._escape_prompt_value(query),
            top_k=top_k,
            categories_data=self._escape_prompt_value(categories_data),
        )

        client = llm_client or self._get_llm_client()
        llm_response = await client.chat(prompt)
        return self._parse_llm_category_response(llm_response, store, categories=category_pool)

    async def _llm_rank_entries(
        self,
        query: str,
        top_k: int,
        doc_hits: list[dict[str, Any]],
        ctx: Context,
        store: Database,
        llm_client: Any | None = None,
        entries: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Use LLM to rank a single lane's entries directly (no per-doc filtering).

        Coarse lane docs (``doc_hits``) are passed only as relevance context; all
        entries of the lane are candidates so retrieval stays single-pass.
        """
        entry_pool = entries if entries is not None else store.entry_repo.list_entries()
        if not entry_pool:
            return []

        items_data = self._format_items_for_llm(store, items=entry_pool)
        if items_data == "No memory items available.":
            return []

        relevant_docs_info = "\n".join([
            f"- {doc.get('title') or doc.get('name', '')}: {doc.get('summary') or doc.get('description', '')}"
            for doc in doc_hits
        ])

        prompt = LLM_ITEM_RANKER_PROMPT.format(
            query=self._escape_prompt_value(query),
            top_k=top_k,
            relevant_categories=self._escape_prompt_value(relevant_docs_info),
            items_data=self._escape_prompt_value(items_data),
        )

        client = llm_client or self._get_llm_client()
        llm_response = await client.chat(prompt)
        return self._parse_llm_item_response(llm_response, store, items=entry_pool)

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

        item_pool = items if items is not None else store.entry_repo.list_entries(lane="memory")
        resource_pool = resources if resources is not None else store.resource_repo.resources
        resources_data = self._format_resources_for_llm(store, item_ids, items=item_pool, resources=resource_pool)
        if resources_data == "No resources available.":
            return []

        # Build context info
        context_parts = []
        if category_hits:
            context_parts.append("Relevant Categories:")
            context_parts.extend([f"- {cat.get('title') or cat.get('name', '')}" for cat in category_hits])
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
        llm_response = await client.chat(prompt)
        return self._parse_llm_resource_response(llm_response, store, resources=resource_pool)

    def _parse_llm_category_response(
        self, raw_response: str, store: Database, categories: Mapping[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Parse LLM category ranking response"""
        category_pool = categories if categories is not None else store.resource_repo.list_resources(lane="memory")
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
        item_pool = items if items is not None else store.entry_repo.list_entries(lane="memory")
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
