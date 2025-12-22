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
        _get_llm_client: Callable[..., Any]
        _model_dump_without_embeddings: Callable[[BaseModel], dict[str, Any]]
        _extract_json_blob: Callable[[str], str]
        _escape_prompt_value: Callable[[str], str]

    async def retrieve(
        self,
        queries: list[dict[str, Any]],
        user: BaseModel | None = None,
    ) -> dict[str, Any]:
        if not queries:
            raise ValueError("empty_queries")
        ctx = self._get_context()
        store = self._get_database()
        original_query = self._extract_query_text(queries[-1])
        await self._ensure_categories_ready(ctx, store)

        context_queries_objs = queries[:-1] if len(queries) > 1 else []

        workflow_name = "retrieve_llm" if self.retrieve_config.method == "llm" else "retrieve_rag"

        state: WorkflowState = {
            "original_query": original_query,
            "context_queries": context_queries_objs,
            "ctx": ctx,
            "store": store,
            "top_k": self.retrieve_config.top_k,
            "skip_rewrite": len(queries) == 1,
            "method": self.retrieve_config.method,
        }

        result = await self._run_workflow(workflow_name, state)
        response = cast(dict[str, Any] | None, result.get("response"))
        if response is None:
            msg = "Retrieve workflow failed to produce a response"
            raise RuntimeError(msg)
        return response

    def _build_rag_retrieve_workflow(self) -> list[WorkflowStep]:
        steps = [
            WorkflowStep(
                step_id="route_intention",
                role="route_intention",
                handler=self._rag_route_intention,
                requires={"original_query", "context_queries", "skip_rewrite"},
                produces={"needs_retrieval", "rewritten_query", "active_query", "next_step_query"},
                capabilities={"llm"},
            ),
            WorkflowStep(
                step_id="route_category",
                role="route_category",
                handler=self._rag_route_category,
                requires={"needs_retrieval", "active_query", "top_k", "ctx", "store"},
                produces={"category_hits", "category_summary_lookup", "query_vector"},
                capabilities={"vector"},
            ),
            WorkflowStep(
                step_id="sufficiency_after_category",
                role="sufficiency_check",
                handler=self._rag_category_sufficiency,
                requires={"needs_retrieval", "active_query", "context_queries", "category_hits", "ctx", "store"},
                produces={"next_step_query", "proceed_to_items", "query_vector"},
                capabilities={"llm"},
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
                    "active_query",
                    "top_k",
                    "query_vector",
                },
                produces={"item_hits", "query_vector"},
                capabilities={"vector"},
            ),
            WorkflowStep(
                step_id="sufficiency_after_items",
                role="sufficiency_check",
                handler=self._rag_item_sufficiency,
                requires={"needs_retrieval", "active_query", "context_queries", "item_hits", "ctx", "store"},
                produces={"next_step_query", "proceed_to_resources", "query_vector"},
                capabilities={"llm"},
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
                    "active_query",
                    "top_k",
                    "query_vector",
                },
                produces={"resource_hits", "query_vector"},
                capabilities={"vector"},
            ),
            WorkflowStep(
                step_id="build_context",
                role="build_context",
                handler=self._rag_build_context,
                requires={"needs_retrieval", "original_query", "rewritten_query", "ctx", "store"},
                produces={"response"},
                capabilities=set(),
            ),
        ]
        return steps

    async def _rag_route_intention(self, state: WorkflowState, step_context: Any) -> WorkflowState:
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
        if not state.get("needs_retrieval"):
            state["category_hits"] = []
            state["category_summary_lookup"] = {}
            state["query_vector"] = None
            return state

        llm_client = self._get_step_llm_client(step_context)
        store = state["store"]
        qvec = (await llm_client.embed([state["active_query"]]))[0]
        hits, summary_lookup = await self._rank_categories_by_summary(
            qvec,
            state["top_k"],
            state["ctx"],
            store,
            embed_client=llm_client,
        )
        state.update({
            "query_vector": qvec,
            "category_hits": hits,
            "category_summary_lookup": summary_lookup,
        })
        return state

    async def _rag_category_sufficiency(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("needs_retrieval"):
            state["proceed_to_items"] = False
            return state

        retrieved_content = ""
        hits = state.get("category_hits") or []
        if hits:
            store = state["store"]
            retrieved_content = self._format_category_content(
                hits,
                state.get("category_summary_lookup", {}),
                store,
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
            state["query_vector"] = (await llm_client.embed([state["active_query"]]))[0]
        return state

    async def _rag_recall_items(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("needs_retrieval") or not state.get("proceed_to_items"):
            state["item_hits"] = []
            return state

        store = state["store"]
        llm_client = self._get_step_llm_client(step_context)
        qvec = state.get("query_vector")
        if qvec is None:
            qvec = (await llm_client.embed([state["active_query"]]))[0]
            state["query_vector"] = qvec
        state["item_hits"] = store.memory_item_repo.vector_search_items(qvec, state["top_k"])
        return state

    async def _rag_item_sufficiency(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("needs_retrieval"):
            state["proceed_to_resources"] = False
            return state

        store = state["store"]
        retrieved_content = ""
        hits = state.get("item_hits") or []
        if hits:
            retrieved_content = self._format_item_content(hits, store)

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
            state["query_vector"] = (await llm_client.embed([state["active_query"]]))[0]
        return state

    async def _rag_recall_resources(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("needs_retrieval") or not state.get("proceed_to_resources"):
            state["resource_hits"] = []
            return state

        store = state["store"]
        corpus = self._resource_caption_corpus(store)
        if not corpus:
            state["resource_hits"] = []
            return state

        llm_client = self._get_step_llm_client(step_context)
        qvec = state.get("query_vector")
        if qvec is None:
            qvec = (await llm_client.embed([state["active_query"]]))[0]
            state["query_vector"] = qvec
        state["resource_hits"] = cosine_topk(qvec, corpus, k=state["top_k"])
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
            response["categories"] = self._materialize_hits(
                state.get("category_hits", []), store.memory_category_repo.categories
            )
            response["items"] = self._materialize_hits(state.get("item_hits", []), store.memory_item_repo.items)
            response["resources"] = self._materialize_hits(
                state.get("resource_hits", []), store.resource_repo.resources
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
            ),
            WorkflowStep(
                step_id="route_category",
                role="route_category",
                handler=self._llm_route_category,
                requires={"needs_retrieval", "active_query", "top_k", "ctx", "store"},
                produces={"category_hits"},
                capabilities={"llm"},
            ),
            WorkflowStep(
                step_id="sufficiency_after_category",
                role="sufficiency_check",
                handler=self._llm_category_sufficiency,
                requires={"needs_retrieval", "active_query", "context_queries", "category_hits"},
                produces={"next_step_query", "proceed_to_items"},
                capabilities={"llm"},
            ),
            WorkflowStep(
                step_id="recall_items",
                role="recall_items",
                handler=self._llm_recall_items,
                requires={
                    "needs_retrieval",
                    "proceed_to_items",
                    "top_k",
                    "ctx",
                    "store",
                    "active_query",
                    "category_hits",
                },
                produces={"item_hits"},
                capabilities={"llm"},
            ),
            WorkflowStep(
                step_id="sufficiency_after_items",
                role="sufficiency_check",
                handler=self._llm_item_sufficiency,
                requires={"needs_retrieval", "active_query", "context_queries", "item_hits"},
                produces={"next_step_query", "proceed_to_resources"},
                capabilities={"llm"},
            ),
            WorkflowStep(
                step_id="recall_resources",
                role="recall_resources",
                handler=self._llm_recall_resources,
                requires={
                    "needs_retrieval",
                    "proceed_to_resources",
                    "active_query",
                    "top_k",
                    "ctx",
                    "store",
                    "item_hits",
                    "category_hits",
                },
                produces={"resource_hits"},
                capabilities={"llm"},
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
        hits = await self._llm_rank_categories(
            state["active_query"],
            state["top_k"],
            state["ctx"],
            store,
            llm_client=llm_client,
        )
        state["category_hits"] = hits
        return state

    async def _llm_category_sufficiency(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("needs_retrieval"):
            state["proceed_to_items"] = False
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

        category_ids = [cat["id"] for cat in state.get("category_hits", [])]
        llm_client = self._get_step_llm_client(step_context)
        store = state["store"]
        state["item_hits"] = await self._llm_rank_items(
            state["active_query"],
            state["top_k"],
            category_ids,
            state.get("category_hits", []),
            state["ctx"],
            store,
            llm_client=llm_client,
        )
        return state

    async def _llm_item_sufficiency(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("needs_retrieval"):
            state["proceed_to_resources"] = False
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
        state["resource_hits"] = await self._llm_rank_resources(
            state["active_query"],
            state["top_k"],
            state.get("category_hits", []),
            state.get("item_hits", []),
            state["ctx"],
            store,
            llm_client=llm_client,
        )
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
    ) -> tuple[list[tuple[str, float]], dict[str, str]]:
        entries = [(cid, cat.summary) for cid, cat in store.memory_category_repo.categories.items() if cat.summary]
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

        prompt = PRE_RETRIEVAL_USER_PROMPT.format(
            query=self._escape_prompt_value(query),
            conversation_history=self._escape_prompt_value(history_text),
            retrieved_content=self._escape_prompt_value(content_text),
        )

        sys_prompt = system_prompt or PRE_RETRIEVAL_SYSTEM_PROMPT
        client = llm_client or self._get_llm_client()
        response = await client.summarize(prompt, system_prompt=sys_prompt)
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
    ) -> dict[str, Any]:
        """Embedding-based retrieval with query rewriting and judging at each tier"""
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
        )
        if cat_hits:
            response["categories"] = self._materialize_hits(cat_hits, store.memory_category_repo.categories)
            content_sections.append(self._format_category_content(cat_hits, summary_lookup, store))

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
        item_hits = store.memory_item_repo.vector_search_items(qvec, top_k)
        if item_hits:
            response["items"] = self._materialize_hits(item_hits, store.memory_item_repo.items)
            content_sections.append(self._format_item_content(item_hits, store))

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
        resource_corpus = self._resource_caption_corpus(store)
        if resource_corpus:
            res_hits = cosine_topk(qvec, resource_corpus, k=top_k)
            if res_hits:
                response["resources"] = self._materialize_hits(res_hits, store.resource_repo.resources)
                content_sections.append(self._format_resource_content(res_hits, store))

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
        self, hits: list[tuple[str, float]], summaries: dict[str, str], store: Database
    ) -> str:
        lines = []
        for cid, score in hits:
            cat = store.memory_category_repo.categories.get(cid)
            if not cat:
                continue
            summary = summaries.get(cid) or cat.summary or ""
            lines.append(f"Category: {cat.name}\nSummary: {summary}\nScore: {score:.3f}")
        return "\n\n".join(lines).strip()

    def _format_item_content(self, hits: list[tuple[str, float]], store: Database) -> str:
        lines = []
        for iid, score in hits:
            item = store.memory_item_repo.items.get(iid)
            if not item:
                continue
            lines.append(f"Memory Item ({item.memory_type}): {item.summary}\nScore: {score:.3f}")
        return "\n\n".join(lines).strip()

    def _format_resource_content(self, hits: list[tuple[str, float]], store: Database) -> str:
        lines = []
        for rid, score in hits:
            res = store.resource_repo.resources.get(rid)
            if not res:
                continue
            caption = res.caption or f"Resource {res.url}"
            lines.append(f"Resource: {caption}\nScore: {score:.3f}")
        return "\n\n".join(lines).strip()

    def _resource_caption_corpus(self, store: Database) -> list[tuple[str, list[float]]]:
        corpus: list[tuple[str, list[float]]] = []
        for rid, res in store.resource_repo.resources.items():
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
    ) -> dict[str, Any]:
        """
        LLM-based retrieval that uses language model to search and rank results
        in a hierarchical manner, with query rewriting and judging at each tier.

        Flow:
        1. Search categories with LLM, judge + rewrite query
        2. If needs more, search items from relevant categories, judge + rewrite
        3. If needs more, search resources related to context
        """
        current_query = query
        client = llm_client or self._get_llm_client()
        response: dict[str, Any] = {"resources": [], "items": [], "categories": [], "next_step_query": None}
        content_sections: list[str] = []

        # Tier 1: Search and rank categories
        category_hits = await self._llm_rank_categories(current_query, top_k, ctx, store, llm_client=client)
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
        )
        if resource_hits:
            response["resources"] = resource_hits
            content_sections.append(self._format_llm_resource_content(resource_hits))

        return response

    def _format_categories_for_llm(self, store: Database, category_ids: list[str] | None = None) -> str:
        """Format categories for LLM consumption"""
        categories_to_format = store.memory_category_repo.categories
        if category_ids:
            categories_to_format = {
                cid: cat for cid, cat in store.memory_category_repo.categories.items() if cid in category_ids
            }

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

    def _format_items_for_llm(self, store: Database, category_ids: list[str] | None = None) -> str:
        """Format memory items for LLM consumption, optionally filtered by category"""
        items_to_format = []
        seen_item_ids = set()

        if category_ids:
            # Get items that belong to the specified categories
            for rel in store.category_item_repo.relations:
                if rel.category_id in category_ids:
                    item = store.memory_item_repo.items.get(rel.item_id)
                    if item and item.id not in seen_item_ids:
                        items_to_format.append(item)
                        seen_item_ids.add(item.id)
        else:
            items_to_format = list(store.memory_item_repo.items.values())

        if not items_to_format:
            return "No memory items available."

        lines = []
        for item in items_to_format:
            lines.append(f"ID: {item.id}")
            lines.append(f"Type: {item.memory_type}")
            lines.append(f"Summary: {item.summary}")
            lines.append("---")

        return "\n".join(lines)

    def _format_resources_for_llm(self, store: Database, item_ids: list[str] | None = None) -> str:
        """Format resources for LLM consumption, optionally filtered by related items"""
        resources_to_format = []

        if item_ids:
            # Get resources that are related to the specified items
            resource_ids = {
                store.memory_item_repo.items[iid].resource_id for iid in item_ids if iid in store.memory_item_repo.items
            }
            resources_to_format = [
                store.resource_repo.resources[rid] for rid in resource_ids if rid in store.resource_repo.resources
            ]
        else:
            resources_to_format = list(store.resource_repo.resources.values())

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
        self, query: str, top_k: int, ctx: Context, store: Database, llm_client: Any | None = None
    ) -> list[dict[str, Any]]:
        """Use LLM to rank categories based on query relevance"""
        if not store.memory_category_repo.categories:
            return []

        categories_data = self._format_categories_for_llm(store)
        prompt = LLM_CATEGORY_RANKER_PROMPT.format(
            query=self._escape_prompt_value(query),
            top_k=top_k,
            categories_data=self._escape_prompt_value(categories_data),
        )

        client = llm_client or self._get_llm_client()
        llm_response = await client.summarize(prompt, system_prompt=None)
        return self._parse_llm_category_response(llm_response, store)

    async def _llm_rank_items(
        self,
        query: str,
        top_k: int,
        category_ids: list[str],
        category_hits: list[dict[str, Any]],
        ctx: Context,
        store: Database,
        llm_client: Any | None = None,
    ) -> list[dict[str, Any]]:
        """Use LLM to rank memory items from relevant categories"""
        if not category_ids:
            print("[LLM Rank Items] No category_ids provided")
            return []

        items_data = self._format_items_for_llm(store, category_ids)
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
        return self._parse_llm_item_response(llm_response, store)

    async def _llm_rank_resources(
        self,
        query: str,
        top_k: int,
        category_hits: list[dict[str, Any]],
        item_hits: list[dict[str, Any]],
        ctx: Context,
        store: Database,
        llm_client: Any | None = None,
    ) -> list[dict[str, Any]]:
        """Use LLM to rank resources related to the context"""
        # Get item IDs to filter resources
        item_ids = [item["id"] for item in item_hits]
        if not item_ids:
            return []

        resources_data = self._format_resources_for_llm(store, item_ids)
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
        return self._parse_llm_resource_response(llm_response, store)

    def _parse_llm_category_response(self, raw_response: str, store: Database) -> list[dict[str, Any]]:
        """Parse LLM category ranking response"""
        results = []
        try:
            json_blob = self._extract_json_blob(raw_response)
            parsed = json.loads(json_blob)

            if "categories" in parsed and isinstance(parsed["categories"], list):
                category_ids = parsed["categories"]
                # Return categories in the order provided by LLM (already sorted by relevance)
                for cat_id in category_ids:
                    if isinstance(cat_id, str):
                        cat = store.memory_category_repo.categories.get(cat_id)
                        if cat:
                            cat_data = self._model_dump_without_embeddings(cat)
                            results.append(cat_data)
        except Exception as e:
            logger.warning(f"Failed to parse LLM category ranking response: {e}")

        return results

    def _parse_llm_item_response(self, raw_response: str, store: Database) -> list[dict[str, Any]]:
        """Parse LLM item ranking response"""
        results = []
        try:
            json_blob = self._extract_json_blob(raw_response)
            parsed = json.loads(json_blob)

            if "items" in parsed and isinstance(parsed["items"], list):
                item_ids = parsed["items"]
                # Return items in the order provided by LLM (already sorted by relevance)
                for item_id in item_ids:
                    if isinstance(item_id, str):
                        mem_item = store.memory_item_repo.items.get(item_id)
                        if mem_item:
                            item_data = self._model_dump_without_embeddings(mem_item)
                            results.append(item_data)
        except Exception as e:
            logger.warning(f"Failed to parse LLM item ranking response: {e}")

        return results

    def _parse_llm_resource_response(self, raw_response: str, store: Database) -> list[dict[str, Any]]:
        """Parse LLM resource ranking response"""
        results = []
        try:
            json_blob = self._extract_json_blob(raw_response)
            parsed = json.loads(json_blob)

            if "resources" in parsed and isinstance(parsed["resources"], list):
                resource_ids = parsed["resources"]
                # Return resources in the order provided by LLM (already sorted by relevance)
                for res_id in resource_ids:
                    if isinstance(res_id, str):
                        res = store.resource_repo.resources.get(res_id)
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
