from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from memu.prompts.retrieve.llm_category_ranker import PROMPT as LLM_CATEGORY_RANKER_PROMPT
from memu.prompts.retrieve.llm_item_ranker import PROMPT as LLM_ITEM_RANKER_PROMPT
from memu.prompts.retrieve.llm_resource_ranker import PROMPT as LLM_RESOURCE_RANKER_PROMPT
from memu.workflow.step import WorkflowState, WorkflowStep

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from memu.app.service import Context
    from memu.app.settings import RetrieveConfig
    from memu.database.interfaces import Database


class RetrieveLlmMixin:
    """LLM-driven retrieve pipeline (``retrieve_llm``).

    This is a sibling of :class:`RetrieveMixin` (which owns the RAG pipeline and
    the shared helpers). Both are composed onto ``MemoryService``; the handlers
    here resolve shared dependencies (e.g. ``_decide_if_retrieval_needed``) at
    runtime through the final service instance.
    """

    if TYPE_CHECKING:
        retrieve_config: RetrieveConfig
        _get_step_llm_client: Callable[[Mapping[str, Any] | None], Any]
        _get_llm_client: Callable[..., Any]
        _decide_if_retrieval_needed: Callable[..., Awaitable[tuple[bool, str]]]
        _model_dump_without_embeddings: Callable[[BaseModel], dict[str, Any]]
        _extract_json_blob: Callable[[str], str]
        _escape_prompt_value: Callable[[str], str]

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
        category_hits = state.get("category_hits", [])
        category_ids = [cat["id"] for cat in category_hits]
        llm_client = self._get_step_llm_client(step_context)
        store = state["store"]

        use_refs = getattr(self.retrieve_config.item, "use_category_references", False)
        ref_ids: list[str] = []
        if use_refs and category_hits:
            # Extract all ref_ids from category summaries
            from memu.utils.references import extract_references

            for cat in category_hits:
                summary = cat.get("summary") or ""
                ref_ids.extend(extract_references(summary))
        if ref_ids:
            # Query items by ref_ids
            items_pool = store.memory_item_repo.list_items_by_ref_ids(ref_ids, where_filters)
        else:
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
        llm_response = await client.chat(prompt)
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
        llm_response = await client.chat(prompt)
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
        llm_response = await client.chat(prompt)
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
