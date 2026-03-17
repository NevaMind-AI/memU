"""
Tests for BM25 retriever, RRF hybrid fusion, and shared helpers.
"""

from __future__ import annotations

from typing import ClassVar, Literal, cast

import pytest

from memu.app.retrieve import VALID_RETRIEVERS, RetrieveMixin
from memu.app.service import MemoryService
from memu.app.settings import RetrieveConfig


# --- Config normalization ---
class TestRetrieveConfigBm25Normalize:
    """retriever field: bm25/hybrid case normalization."""

    def test_bm25_uppercase(self):
        c = RetrieveConfig(retriever=cast(Literal["vector", "keyword", "bm25", "hybrid"], "BM25"))
        assert c.retriever == "bm25"

    def test_bm25_mixed_case(self):
        c = RetrieveConfig(retriever=cast(Literal["vector", "keyword", "bm25", "hybrid"], "Bm25"))
        assert c.retriever == "bm25"

    def test_hybrid_uppercase(self):
        c = RetrieveConfig(retriever=cast(Literal["vector", "keyword", "bm25", "hybrid"], "HYBRID"))
        assert c.retriever == "hybrid"

    def test_hybrid_mixed_case(self):
        c = RetrieveConfig(retriever=cast(Literal["vector", "keyword", "bm25", "hybrid"], "Hybrid"))
        assert c.retriever == "hybrid"


# --- VALID_RETRIEVERS constant ---
class TestValidRetrievers:
    """Module-level VALID_RETRIEVERS constant is used for validation."""

    def test_contains_all_options(self):
        assert {"vector", "keyword", "bm25", "hybrid"} == VALID_RETRIEVERS

    def test_invalid_retriever_error_message_includes_all(self):
        from memu.app.retrieve import InvalidRetrieverError

        err = InvalidRetrieverError()
        msg = str(err).lower()
        for r in VALID_RETRIEVERS:
            assert r in msg, f"Expected '{r}' in error message: {msg}"


# --- _extract_item_text helper ---
class TestExtractItemText:
    """Shared helper to extract searchable text from items."""

    def test_dict_item_summary_only(self):
        item = {"summary": "coffee and tea", "extra": {}}
        assert RetrieveMixin._extract_item_text(item) == "coffee and tea"

    def test_dict_item_summary_and_extra(self):
        item = {"summary": "coffee", "extra": {"tag": "morning"}}
        assert RetrieveMixin._extract_item_text(item) == "coffee morning"

    def test_dict_item_skips_none_extra(self):
        item = {"summary": "coffee", "extra": {"a": "milk", "b": None}}
        assert RetrieveMixin._extract_item_text(item) == "coffee milk"

    def test_object_item(self):
        class FakeItem:
            summary = "hello world"
            extra: ClassVar[dict[str, str]] = {"k": "v"}

        assert RetrieveMixin._extract_item_text(FakeItem()) == "hello world v"

    def test_empty_summary(self):
        item = {"summary": "", "extra": {}}
        assert RetrieveMixin._extract_item_text(item) == ""


# --- BM25 scoring ---
class TestBm25ScoreItems:
    """_bm25_score_items: Okapi BM25 scoring."""

    def test_basic_match(self):
        pool = {
            "id1": {"summary": "coffee and tea", "extra": {}},
            "id2": {"summary": "only water", "extra": {}},
        }
        out = RetrieveMixin._bm25_score_items("coffee", pool, top_k=5)
        assert len(out) >= 1
        assert out[0][0] == "id1"
        assert out[0][1] > 0

    def test_rare_term_ranks_higher(self):
        """BM25 IDF: a rare term should score higher than a common one."""
        pool = {
            "a": {"summary": "common common rare", "extra": {}},
            "b": {"summary": "common common common", "extra": {}},
            "c": {"summary": "common", "extra": {}},
        }
        out = RetrieveMixin._bm25_score_items("rare", pool, top_k=5)
        # Only "a" has "rare"
        assert len(out) == 1
        assert out[0][0] == "a"

    def test_empty_query(self):
        pool = {"id1": {"summary": "something", "extra": {}}}
        assert RetrieveMixin._bm25_score_items("", pool, top_k=5) == []

    def test_empty_pool(self):
        assert RetrieveMixin._bm25_score_items("query", {}, top_k=5) == []

    def test_top_k_respected(self):
        pool = {f"id{i}": {"summary": f"word{i} common", "extra": {}} for i in range(10)}
        out = RetrieveMixin._bm25_score_items("common", pool, top_k=3)
        assert len(out) <= 3

    def test_returns_list_of_tuples(self):
        pool = {"id1": {"summary": "hello world", "extra": {}}}
        out = RetrieveMixin._bm25_score_items("hello", pool, top_k=5)
        assert isinstance(out, list)
        assert all(isinstance(t, tuple) and len(t) == 2 for t in out)
        assert all(isinstance(t[0], str) and isinstance(t[1], float) for t in out)

    def test_stable_sort_by_id_on_tie(self):
        """When scores are equal, sort by ID ascending for determinism."""
        pool = {
            "b": {"summary": "x", "extra": {}},
            "a": {"summary": "x", "extra": {}},
        }
        out = RetrieveMixin._bm25_score_items("x", pool, top_k=5)
        ids = [t[0] for t in out]
        assert ids == ["a", "b"]

    def test_uses_extra_values(self):
        pool = {
            "id1": {"summary": "summary", "extra": {"tag": "coffee"}},
        }
        out = RetrieveMixin._bm25_score_items("coffee", pool, top_k=5)
        assert len(out) == 1 and out[0][0] == "id1"


# --- RRF fusion ---
class TestRrfFuse:
    """_rrf_fuse: Reciprocal Rank Fusion of multiple ranked lists."""

    def test_single_list(self):
        ranked = [("a", 5.0), ("b", 3.0)]
        out = RetrieveMixin._rrf_fuse(ranked, top_k=5)
        assert out[0][0] == "a"
        assert out[1][0] == "b"

    def test_items_in_both_lists_rank_higher(self):
        list1 = [("a", 5.0), ("b", 3.0)]
        list2 = [("a", 4.0), ("c", 2.0)]
        out = RetrieveMixin._rrf_fuse(list1, list2, top_k=5)
        # "a" appears in both, should be first
        assert out[0][0] == "a"

    def test_disjoint_lists(self):
        list1 = [("a", 5.0)]
        list2 = [("b", 3.0)]
        out = RetrieveMixin._rrf_fuse(list1, list2, top_k=5)
        assert len(out) == 2
        ids = {t[0] for t in out}
        assert ids == {"a", "b"}

    def test_top_k_respected(self):
        list1 = [("a", 5.0), ("b", 3.0), ("c", 1.0)]
        list2 = [("d", 4.0), ("e", 2.0), ("f", 0.5)]
        out = RetrieveMixin._rrf_fuse(list1, list2, top_k=2)
        assert len(out) == 2

    def test_stable_sort_on_tie(self):
        """Same RRF score => sort by ID ascending."""
        list1 = [("b", 5.0)]
        list2 = [("a", 5.0)]
        out = RetrieveMixin._rrf_fuse(list1, list2, top_k=5)
        # Both have same RRF score (1/(60+1)), tie-break by ID
        assert out[0][0] == "a"
        assert out[1][0] == "b"

    def test_empty_lists(self):
        assert RetrieveMixin._rrf_fuse(top_k=5) == []

    def test_rrf_scores_are_positive(self):
        list1 = [("a", 5.0), ("b", 3.0)]
        out = RetrieveMixin._rrf_fuse(list1, top_k=5)
        assert all(score > 0 for _, score in out)


# --- Per-call override tests ---
class TestRetrieveBm25Override:
    """Per-call retriever='bm25' and retriever='hybrid' override."""

    @pytest.mark.asyncio
    async def test_retrieve_rag_bm25_state_and_workflow(self, monkeypatch: pytest.MonkeyPatch):
        service = MemoryService(
            database_config={"metadata_store": {"provider": "inmemory"}},
            retrieve_config={"method": "rag", "retriever": "vector"},
        )
        captured: list[tuple[str, dict]] = []

        async def fake_run(workflow_name: str, state: dict):
            captured.append((workflow_name, dict(state)))
            return {
                "response": {
                    "categories": [],
                    "items": [],
                    "resources": [],
                    "needs_retrieval": True,
                    "original_query": "q",
                    "rewritten_query": "q",
                    "next_step_query": None,
                }
            }

        monkeypatch.setattr(service, "_run_workflow", fake_run, raising=True)
        queries = [{"role": "user", "content": {"text": "q"}}]
        await service.retrieve(queries, method="rag", retriever="bm25")
        assert len(captured) == 1
        wname, state = captured[0]
        assert wname == "retrieve_rag"
        assert state.get("retriever") == "bm25"

    @pytest.mark.asyncio
    async def test_retrieve_rag_hybrid_state_and_workflow(self, monkeypatch: pytest.MonkeyPatch):
        service = MemoryService(
            database_config={"metadata_store": {"provider": "inmemory"}},
            retrieve_config={"method": "rag", "retriever": "vector"},
        )
        captured: list[tuple[str, dict]] = []

        async def fake_run(workflow_name: str, state: dict):
            captured.append((workflow_name, dict(state)))
            return {
                "response": {
                    "categories": [],
                    "items": [],
                    "resources": [],
                    "needs_retrieval": True,
                    "original_query": "q",
                    "rewritten_query": "q",
                    "next_step_query": None,
                }
            }

        monkeypatch.setattr(service, "_run_workflow", fake_run, raising=True)
        queries = [{"role": "user", "content": {"text": "q"}}]
        await service.retrieve(queries, method="rag", retriever="hybrid")
        assert len(captured) == 1
        _, state = captured[0]
        assert state.get("retriever") == "hybrid"

    @pytest.mark.asyncio
    async def test_invalid_retriever_still_raises(self):
        service = MemoryService(
            database_config={"metadata_store": {"provider": "inmemory"}},
            retrieve_config={"method": "rag"},
        )
        queries = [{"role": "user", "content": {"text": "q"}}]
        with pytest.raises(ValueError) as exc_info:
            await service.retrieve(queries, method="rag", retriever="INVALID")
        msg = str(exc_info.value).lower()
        assert "bm25" in msg
        assert "hybrid" in msg
        assert "vector" in msg
        assert "keyword" in msg
