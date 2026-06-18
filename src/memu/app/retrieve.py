from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel

from memu.database.inmemory.vector import cosine_topk
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

    def _extract_referenced_item_ids(self, state: WorkflowState) -> set[str]:
        """Extract item IDs from category summary references."""
        from memu.utils.references import extract_references

        category_hits = state.get("category_hits") or []
        summary_lookup = state.get("category_summary_lookup", {})
        category_pool = state.get("category_pool") or {}
        referenced_item_ids: set[str] = set()

        for cid, _score in category_hits:
            # Get summary from lookup or category
            summary = summary_lookup.get(cid)
            if not summary:
                cat = category_pool.get(cid)
                if cat:
                    summary = cat.summary
            if summary:
                refs = extract_references(summary)
                referenced_item_ids.update(refs)

        return referenced_item_ids

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
            ranking=self.retrieve_config.item.ranking,
            recency_decay_days=self.retrieve_config.item.recency_decay_days,
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
        client = embed_client or self._get_embedding_client()
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

    def _resource_caption_corpus(
        self, store: Database, resources: Mapping[str, Any] | None = None
    ) -> list[tuple[str, list[float]]]:
        resource_pool = resources if resources is not None else store.resource_repo.resources
        corpus: list[tuple[str, list[float]]] = []
        for rid, res in resource_pool.items():
            if res.embedding:
                corpus.append((rid, res.embedding))
        return corpus
