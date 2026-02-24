from __future__ import annotations

import json
import logging
import math
import re
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal, cast

from pydantic import BaseModel

from memu.database.inmemory.vector import cosine_topk
from memu.prompts.retrieve.llm_category_ranker import PROMPT as LLM_CATEGORY_RANKER_PROMPT
from memu.prompts.retrieve.llm_item_ranker import PROMPT as LLM_ITEM_RANKER_PROMPT
from memu.prompts.retrieve.llm_resource_ranker import PROMPT as LLM_RESOURCE_RANKER_PROMPT
from memu.prompts.retrieve.pre_retrieval_decision import SYSTEM_PROMPT as PRE_RETRIEVAL_SYSTEM_PROMPT
from memu.prompts.retrieve.pre_retrieval_decision import USER_PROMPT as PRE_RETRIEVAL_USER_PROMPT
from memu.workflow.step import WorkflowState, WorkflowStep

logger = logging.getLogger(__name__)

VALID_RETRIEVERS = {"vector", "keyword", "bm25", "hybrid"}

if TYPE_CHECKING:
    from memu.app.service import Context
    from memu.app.settings import RetrieveConfig
    from memu.database.interfaces import Database


class InvalidRetrieverError(ValueError):
    def __init__(self) -> None:
        super().__init__(f"retriever must be one of: {', '.join(sorted(VALID_RETRIEVERS))}")


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
        method: Literal["rag", "llm"] | None = None,
        retriever: str | None = None,
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

        effective_method = method if method is not None else self.retrieve_config.method
        workflow_name = "retrieve_llm" if effective_method == "llm" else "retrieve_rag"

        if effective_method == "rag":
            effective_retriever = (
                retriever.lower() if retriever is not None else getattr(self.retrieve_config, "retriever", "vector")
            )
            if retriever is not None and effective_retriever not in VALID_RETRIEVERS:
                raise InvalidRetrieverError()
        else:
            effective_retriever = None

        state: WorkflowState = {
            "method": effective_method,
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
        if effective_method == "rag":
            state["retriever"] = effective_retriever

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

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Split text into lowercase non-empty tokens (standard library only)."""
        if not text:
            return set()
        parts = re.split(r"[^\w]+", text.lower())
        return {p for p in parts if p}

    @staticmethod
    def _tokenize_list(text: str) -> list[str]:
        if not text:
            return []
        return [p for p in re.split(r"[^\w]+", text.lower()) if p]

    @staticmethod
    def _extract_item_text(item: Any) -> str:
        """Extract searchable text from an item (summary + extra values)."""
        summary = item.get("summary", "") if isinstance(item, dict) else getattr(item, "summary", "")
        extra = item.get("extra", {}) if isinstance(item, dict) else (getattr(item, "extra", None) or {})
        extra_str = " ".join(str(v) for v in extra.values() if v is not None)
        return f"{summary} {extra_str}".strip()

    @staticmethod
    def _extract_item_field_text(item: Any, field: str | None) -> str:
        """Field-aware text extraction. Supports summary/content and extra.<key> lookups."""
        if not field:
            return RetrieveMixin._extract_item_text(item)
        f = field.lower()
        summary = item.get("summary", "") if isinstance(item, dict) else getattr(item, "summary", "")
        extra = item.get("extra", {}) if isinstance(item, dict) else (getattr(item, "extra", None) or {})
        if f in {"summary", "content", "text"}:
            return str(summary or "")
        if f.startswith("extra."):
            key = f.split(".", 1)[1]
            return str((extra or {}).get(key, "") or "")
        if f == "extra":
            return " ".join(str(v) for v in (extra or {}).values() if v is not None)
        # Fallback: if the key exists in extra, use it.
        if isinstance(extra, dict) and field in extra:
            return str(extra.get(field, "") or "")
        return RetrieveMixin._extract_item_text(item)

    @staticmethod
    def _add_parsed_token(spec: dict[str, Any], field: str | None, body: str, sign: str) -> None:
        """Route a single parsed query token into the appropriate spec bucket."""
        is_phrase = len(body) >= 2 and body[0] == '"' and body[-1] == '"'
        value = body[1:-1].strip().lower() if is_phrase else body.lower()
        if not value:
            return
        if is_phrase:
            if field:
                spec["field_phrases"].append((field, value, sign))
            else:
                spec["phrases"].append((value, sign))
        else:
            tokens = [t for t in re.split(r"[^\w]+", value) if t]
            for tok in tokens:
                if field:
                    spec["field_terms"].append((field, tok, sign))
                elif sign == "must":
                    spec["must_terms"].add(tok)
                elif sign == "exclude":
                    spec["exclude_terms"].add(tok)
                else:
                    spec["should_terms"].add(tok)

    @staticmethod
    def _parse_lexical_query(query: str) -> dict[str, Any]:
        """Parse lexical query syntax.

        Supported forms:
        - exact phrase in quotes: "error code"
        - mandatory token: +token
        - exclusion token: -token
        - field-aware token/phrase: summary:token, extra.source:"slack"
        """
        spec: dict[str, Any] = {
            "should_terms": set(),
            "must_terms": set(),
            "exclude_terms": set(),
            "phrases": [],
            "field_terms": [],  # (field, term, sign)
            "field_phrases": [],  # (field, phrase, sign)
        }
        if not query:
            return spec

        pattern = re.compile(r'(?P<prefix>[+-]?)(?:(?P<field>[A-Za-z_][\w\.]*)\:)?(?P<body>"[^"]+"|\S+)')
        for m in pattern.finditer(query):
            prefix = m.group("prefix") or ""
            field = m.group("field")
            body = (m.group("body") or "").strip()
            if not body:
                continue
            sign = "must" if prefix == "+" else ("exclude" if prefix == "-" else "should")
            RetrieveMixin._add_parsed_token(spec, field, body, sign)

        # If the query had no explicit should/must terms, backfill from plain tokenization.
        if (
            not spec["should_terms"]
            and not spec["must_terms"]
            and not spec["phrases"]
            and not spec["field_terms"]
            and not spec["field_phrases"]
        ):
            spec["should_terms"] = RetrieveMixin._tokenize(query)
        return spec

    @staticmethod
    def _passes_exclusions(item: Any, all_text: str, all_tokens: set[str], spec: Mapping[str, Any]) -> bool:
        """Return False if the item matches any exclusion constraint in spec."""
        if spec.get("exclude_terms", set()) & all_tokens:
            return False
        if any(phrase in all_text for phrase, sign in spec.get("phrases", []) if sign == "exclude"):
            return False
        for field, term, sign in spec.get("field_terms", []):
            if sign == "exclude":
                ftxt = RetrieveMixin._extract_item_field_text(item, field).lower()
                if term in RetrieveMixin._tokenize(ftxt):
                    return False
        for field, phrase, sign in spec.get("field_phrases", []):
            if sign == "exclude":
                ftxt = RetrieveMixin._extract_item_field_text(item, field).lower()
                if phrase in ftxt:
                    return False
        return True

    @staticmethod
    def _satisfies_mandatory(item: Any, all_text: str, all_tokens: set[str], spec: Mapping[str, Any]) -> bool:
        """Return False if the item fails any mandatory constraint in spec."""
        if not (spec.get("must_terms", set()) <= all_tokens):
            return False
        if any(phrase not in all_text for phrase, sign in spec.get("phrases", []) if sign == "must"):
            return False
        for field, term, sign in spec.get("field_terms", []):
            if sign == "must":
                ftxt = RetrieveMixin._extract_item_field_text(item, field).lower()
                if term not in RetrieveMixin._tokenize(ftxt):
                    return False
        for field, phrase, sign in spec.get("field_phrases", []):
            if sign == "must":
                ftxt = RetrieveMixin._extract_item_field_text(item, field).lower()
                if phrase not in ftxt:
                    return False
        return True

    @staticmethod
    def _item_matches_lexical_spec(item: Any, spec: Mapping[str, Any]) -> bool:
        all_text = RetrieveMixin._extract_item_text(item).lower()
        all_tokens = RetrieveMixin._tokenize(all_text)
        return RetrieveMixin._passes_exclusions(
            item, all_text, all_tokens, spec
        ) and RetrieveMixin._satisfies_mandatory(item, all_text, all_tokens, spec)

    @staticmethod
    def _score_keyword_item(item: Any, spec: Mapping[str, Any]) -> float:
        """Compute keyword relevance score for a single item against spec."""
        all_text = RetrieveMixin._extract_item_text(item).lower()
        all_tokens = RetrieveMixin._tokenize(all_text)
        score = 0.0
        score += float(len(spec.get("should_terms", set()) & all_tokens))
        score += 1.5 * float(len(spec.get("must_terms", set()) & all_tokens))
        for phrase, sign in spec.get("phrases", []):
            if sign in {"should", "must"} and phrase in all_text:
                score += 2.0 if sign == "should" else 3.0
        for field, term, sign in spec.get("field_terms", []):
            if sign == "exclude":
                continue
            ftxt = RetrieveMixin._extract_item_field_text(item, field).lower()
            if term in RetrieveMixin._tokenize(ftxt):
                score += 1.5 if sign == "should" else 2.5
        for field, phrase, sign in spec.get("field_phrases", []):
            if sign == "exclude":
                continue
            ftxt = RetrieveMixin._extract_item_field_text(item, field).lower()
            if phrase in ftxt:
                score += 2.5 if sign == "should" else 3.5
        return score

    @staticmethod
    def _keyword_match_items(
        query: str,
        pool: Mapping[str, Any],
        top_k: int,
    ) -> list[tuple[str, float]]:
        """Keyword retrieval with inclusion/exclusion, phrase matching, and field-aware matching."""
        spec = RetrieveMixin._parse_lexical_query(query)
        if not any([
            spec.get("should_terms"),
            spec.get("must_terms"),
            spec.get("phrases"),
            spec.get("field_terms"),
            spec.get("field_phrases"),
        ]):
            return []

        scores: list[tuple[str, float]] = []
        for item_id, item in pool.items():
            if not RetrieveMixin._item_matches_lexical_spec(item, spec):
                continue
            score = RetrieveMixin._score_keyword_item(item, spec)
            # If query only has negatives and item passes, avoid returning everything.
            if score > 0:
                scores.append((item_id, score))
        scores.sort(key=lambda x: (-x[1], x[0]))
        return scores[:top_k]

    @staticmethod
    def _bm25_doc_score(
        query_tokens: Sequence[str],
        doc_tokens: list[str],
        df: Mapping[str, int],
        n_docs: int,
        avgdl: float,
        k1: float,
        b: float,
    ) -> float:
        """Compute BM25 score for a single document."""
        doc_len = max(len(doc_tokens), 1)
        tf_map: dict[str, int] = {}
        for t in doc_tokens:
            tf_map[t] = tf_map.get(t, 0) + 1

        score = 0.0
        for term in query_tokens:
            tf = tf_map.get(term, 0)
            if tf <= 0:
                continue
            n_t = df.get(term, 0)
            idf = math.log((n_docs - n_t + 0.5) / (n_t + 0.5) + 1.0)
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_len / max(avgdl, 1e-9))
            score += idf * numerator / denominator
        return score

    @staticmethod
    def _build_bm25_query_terms(spec: Mapping[str, Any]) -> list[str]:
        """Build ordered, de-duplicated list of positive query terms for BM25 scoring."""
        positive_terms: list[str] = []
        positive_terms.extend(sorted(spec.get("should_terms", set())))
        positive_terms.extend(sorted(spec.get("must_terms", set())))
        for _field, term, sign in spec.get("field_terms", []):
            if sign != "exclude":
                positive_terms.append(term)
        return list(dict.fromkeys(positive_terms))

    @staticmethod
    def _compute_term_df(query_terms: list[str], docs: Mapping[str, list[str]]) -> dict[str, int]:
        """Compute document frequency for each query term across the doc corpus."""
        df: dict[str, int] = dict.fromkeys(query_terms, 0)
        for toks in docs.values():
            uniq = set(toks)
            for term in query_terms:
                if term in uniq:
                    df[term] += 1
        return df

    @staticmethod
    def _apply_bm25_boost(item: Any, spec: Mapping[str, Any]) -> float:
        """Compute phrase and field-aware score boost for BM25 (conservative weights)."""
        all_text = RetrieveMixin._extract_item_text(item).lower()
        boost = 0.0
        for phrase, sign in spec.get("phrases", []):
            if sign != "exclude" and phrase in all_text:
                boost += 0.8 if sign == "should" else 1.2
        for field, phrase, sign in spec.get("field_phrases", []):
            if sign == "exclude":
                continue
            ftxt = RetrieveMixin._extract_item_field_text(item, field).lower()
            if phrase in ftxt:
                boost += 0.8 if sign == "should" else 1.2
        for field, term, sign in spec.get("field_terms", []):
            if sign == "exclude":
                continue
            ftxt = RetrieveMixin._extract_item_field_text(item, field).lower()
            if term in RetrieveMixin._tokenize(ftxt):
                boost += 0.4 if sign == "should" else 0.7
        return boost

    @staticmethod
    def _bm25_score_items(
        query: str,
        pool: Mapping[str, Any],
        top_k: int,
        k1: float = 1.2,
        b: float = 0.75,
    ) -> list[tuple[str, float]]:
        """BM25 with lexical constraints and phrase/field boosts."""
        spec = RetrieveMixin._parse_lexical_query(query)
        query_terms = RetrieveMixin._build_bm25_query_terms(spec)
        if not query_terms and not spec.get("phrases") and not spec.get("field_phrases"):
            return []

        docs: dict[str, list[str]] = {}
        items_filtered: dict[str, Any] = {}
        for item_id, item in pool.items():
            if not RetrieveMixin._item_matches_lexical_spec(item, spec):
                continue
            doc_text = RetrieveMixin._extract_item_text(item)
            docs[item_id] = RetrieveMixin._tokenize_list(doc_text)
            items_filtered[item_id] = item

        if not docs:
            return []

        n_docs = len(docs)
        avgdl = sum(len(toks) for toks in docs.values()) / max(n_docs, 1)
        df = RetrieveMixin._compute_term_df(query_terms, docs)

        scores: list[tuple[str, float]] = []
        for item_id, doc_tokens in docs.items():
            score = RetrieveMixin._bm25_doc_score(query_terms, doc_tokens, df, n_docs, avgdl, k1, b)
            score += RetrieveMixin._apply_bm25_boost(items_filtered[item_id], spec)
            if score > 0:
                scores.append((item_id, score))

        scores.sort(key=lambda x: (-x[1], x[0]))
        return scores[:top_k]

    @staticmethod
    def _rrf_fuse(
        *ranked_lists: list[tuple[str, float]],
        k: int = 60,
        top_k: int = 5,
    ) -> list[tuple[str, float]]:
        """Reciprocal Rank Fusion across multiple ranked result lists."""
        rrf_scores: dict[str, float] = {}
        for ranked_list in ranked_lists:
            for rank, (item_id, _score) in enumerate(ranked_list):
                rrf_scores[item_id] = rrf_scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
        results = list(rrf_scores.items())
        results.sort(key=lambda x: (-x[1], x[0]))
        return results[:top_k]

    async def _rag_recall_items(self, state: WorkflowState, step_context: Any) -> WorkflowState:
        if not state.get("retrieve_item") or not state.get("needs_retrieval") or not state.get("proceed_to_items"):
            state["item_hits"] = []
            return state

        store = state["store"]
        where_filters = state.get("where") or {}
        items_pool = store.memory_item_repo.list_items(where_filters)
        retriever = state.get("retriever") or getattr(self.retrieve_config, "retriever", "vector")

        top_k = self.retrieve_config.item.top_k

        if retriever == "keyword":
            state["item_hits"] = self._keyword_match_items(
                state["active_query"],
                items_pool,
                top_k,
            )
            state["item_pool"] = items_pool
            return state

        if retriever == "bm25":
            state["item_hits"] = self._bm25_score_items(
                state["active_query"],
                items_pool,
                top_k,
            )
            state["item_pool"] = items_pool
            return state

        # Vector search (shared by "vector" and "hybrid")
        qvec = state.get("query_vector")
        if qvec is None:
            embed_client = self._get_step_embedding_client(step_context)
            qvec = (await embed_client.embed([state["active_query"]]))[0]
            state["query_vector"] = qvec
        vector_hits = store.memory_item_repo.vector_search_items(
            qvec,
            top_k,
            where=where_filters,
            ranking=self.retrieve_config.item.ranking,
            recency_decay_days=self.retrieve_config.item.recency_decay_days,
        )

        if retriever == "hybrid":
            bm25_hits = self._bm25_score_items(state["active_query"], items_pool, top_k)
            state["item_hits"] = self._rrf_fuse(bm25_hits, vector_hits, top_k=top_k)
        else:
            state["item_hits"] = vector_hits

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

    def _format_llm_resource_content(self, hits: list[dict[str, Any]]) -> str:
        """Format LLM-ranked resource content for judger"""
        lines = []
        for res in hits:
            caption = res.get("caption", "") or f"Resource {res['url']}"
            lines.append(f"Resource: {caption}")
        return "\n\n".join(lines).strip()
