"""
Tests for keyword retriever (Plan A): config normalize, keyword_match_items, RAG response structure.
No new dependencies; optional integration test guarded by OPENAI_API_KEY skipif.
"""

from __future__ import annotations

import os

import pytest

from memu.app.retrieve import RetrieveMixin
from memu.app.service import MemoryService
from memu.app.settings import RetrieveConfig


# --- 需求 3: TestRetrieveConfigNormalize ---
class TestRetrieveConfigNormalize:
    """retriever field: vector/keyword case normalization via Normalize."""

    def test_vector_uppercase(self):
        c = RetrieveConfig(retriever="VECTOR")
        assert c.retriever == "vector"

    def test_keyword_uppercase(self):
        c = RetrieveConfig(retriever="KEYWORD")
        assert c.retriever == "keyword"

    def test_keyword_mixed_case(self):
        c = RetrieveConfig(retriever="KeyWord")
        assert c.retriever == "keyword"

    def test_default_is_vector(self):
        c = RetrieveConfig()
        assert c.retriever == "vector"


# --- 需求 3: TestKeywordMatchItems ---
class TestKeywordMatchItems:
    """_tokenize and _keyword_match_items: hit, stable sort, top_k, extra, empty query/pool."""

    def test_tokenize_lowercase_and_splits(self):
        assert RetrieveMixin._tokenize("Hello World") == {"hello", "world"}
        assert RetrieveMixin._tokenize("a-b c") == {"a", "b", "c"}

    def test_tokenize_empty(self):
        assert RetrieveMixin._tokenize("") == set()
        assert RetrieveMixin._tokenize("   ") == set()

    def test_keyword_match_hit(self):
        pool = {
            "id1": {"summary": "coffee and tea", "extra": {}},
            "id2": {"summary": "only tea", "extra": {}},
        }
        out = RetrieveMixin._keyword_match_items("coffee", pool, top_k=5)
        assert len(out) == 1
        assert out[0][0] == "id1"
        assert out[0][1] == 1.0

    def test_keyword_match_stable_sort_same_score(self):
        pool = {
            "b": {"summary": "x", "extra": {}},
            "a": {"summary": "x", "extra": {}},
        }
        out = RetrieveMixin._keyword_match_items("x", pool, top_k=5)
        assert out == [("a", 1.0), ("b", 1.0)]

    def test_keyword_match_top_k(self):
        pool = {
            "a": {"summary": "one", "extra": {}},
            "b": {"summary": "two", "extra": {}},
            "c": {"summary": "one two", "extra": {}},
        }
        out = RetrieveMixin._keyword_match_items("one two", pool, top_k=2)
        assert len(out) == 2
        scores = [x[1] for x in out]
        assert scores == sorted(scores, reverse=True)

    def test_keyword_match_extra_values(self):
        pool = {
            "id1": {"summary": "summary", "extra": {"tag": "coffee"}},
        }
        out = RetrieveMixin._keyword_match_items("coffee", pool, top_k=5)
        assert len(out) == 1 and out[0][0] == "id1" and out[0][1] == 1.0

    def test_keyword_match_extra_skips_none(self):
        pool = {
            "id1": {"summary": "summary", "extra": {"a": "word", "b": None}},
        }
        out = RetrieveMixin._keyword_match_items("word", pool, top_k=5)
        assert len(out) == 1 and out[0][1] == 1.0

    def test_keyword_match_empty_query_returns_empty(self):
        pool = {"id1": {"summary": "something", "extra": {}}}
        out = RetrieveMixin._keyword_match_items("", pool, top_k=5)
        assert out == []

    def test_keyword_match_empty_pool_returns_empty(self):
        out = RetrieveMixin._keyword_match_items("query", {}, top_k=5)
        assert out == []


# --- 需求 3: TestRagResponseStructure ---
class TestRagResponseStructure:
    """Assert RAG response dict contains at least categories/items/resources (no new deps)."""

    def test_rag_build_context_response_keys(self):
        service = MemoryService(
            database_config={"metadata_store": {"provider": "inmemory"}},
            retrieve_config={"method": "rag"},
        )
        store = service._get_database()
        state = {
            "needs_retrieval": True,
            "original_query": "q",
            "rewritten_query": "q",
            "next_step_query": None,
            "ctx": service._get_context(),
            "store": store,
            "where": {},
            "category_pool": {},
            "item_pool": {},
            "resource_pool": {},
            "category_hits": [],
            "item_hits": [],
            "resource_hits": [],
        }
        result = service._rag_build_context(state, None)
        assert "response" in result
        r = result["response"]
        assert "categories" in r
        assert "items" in r
        assert "resources" in r
        assert "needs_retrieval" in r
        assert "original_query" in r


# --- 需求 3 可选: OPENAI_API_KEY 集成测试 ---
@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)
class TestRetrieveKeywordIntegration:
    """Optional: full retrieve with retriever=keyword (requires OPENAI_API_KEY)."""

    @pytest.mark.asyncio
    async def test_retrieve_rag_keyword_returns_structure(self):
        service = MemoryService(
            llm_profiles={"default": {"api_key": os.environ["OPENAI_API_KEY"]}},
            database_config={"metadata_store": {"provider": "inmemory"}},
            retrieve_config={"method": "rag", "retriever": "keyword"},
        )
        queries = [{"role": "user", "content": {"text": "test"}}]
        response = await service.retrieve(queries=queries)
        assert "categories" in response
        assert "items" in response
        assert "resources" in response
