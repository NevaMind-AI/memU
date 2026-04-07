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
    """retriever and hybrid fusion fields normalize consistently."""

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

    def test_fusion_strategy_uppercase(self):
        c = RetrieveConfig(fusion_strategy=cast(Literal["rrf", "weighted"], "WEIGHTED"))
        assert c.fusion_strategy == "weighted"

    def test_fusion_strategy_mixed_case(self):
        c = RetrieveConfig(fusion_strategy=cast(Literal["rrf", "weighted"], "RrF"))
        assert c.fusion_strategy == "rrf"

    def test_weighted_alpha_bounds(self):
        with pytest.raises(ValueError):
            RetrieveConfig(weighted_alpha=1.1)

    def test_default_fusion_strategy_is_rrf(self):
        c = RetrieveConfig()
        assert c.fusion_strategy == "rrf"


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


class TestWeightedScoreFuse:
    """Weighted score fusion uses normalized vector and BM25 scores."""

    def test_weighted_prefers_vector_when_alpha_high(self):
        vector_hits = [("semantic", 0.95), ("shared", 0.80)]
        bm25_hits = [("keyword", 10.0), ("shared", 8.0)]
        out = RetrieveMixin._weighted_score_fuse(vector_hits, bm25_hits, alpha=0.8, top_k=5)
        assert out[0][0] == "semantic"

    def test_weighted_prefers_bm25_when_alpha_low(self):
        vector_hits = [("semantic", 0.95), ("shared", 0.80)]
        bm25_hits = [("keyword", 10.0), ("shared", 8.0)]
        out = RetrieveMixin._weighted_score_fuse(vector_hits, bm25_hits, alpha=0.2, top_k=5)
        assert out[0][0] == "keyword"

    def test_weighted_includes_union_of_lists(self):
        vector_hits = [("a", 0.9)]
        bm25_hits = [("b", 2.0)]
        out = RetrieveMixin._weighted_score_fuse(vector_hits, bm25_hits, alpha=0.5, top_k=5)
        ids = [item_id for item_id, _score in out]
        assert ids == ["a", "b"]

    def test_weighted_handles_flat_scores(self):
        vector_hits = [("a", 0.5), ("b", 0.5)]
        bm25_hits = [("a", 1.0), ("c", 1.0)]
        out = RetrieveMixin._weighted_score_fuse(vector_hits, bm25_hits, alpha=0.5, top_k=5)
        assert out[0] == ("a", 1.0)

    def test_weighted_top_k_respected(self):
        vector_hits = [("a", 3.0), ("b", 2.0), ("c", 1.0)]
        bm25_hits = [("d", 3.0), ("e", 2.0), ("f", 1.0)]
        out = RetrieveMixin._weighted_score_fuse(vector_hits, bm25_hits, alpha=0.5, top_k=2)
        assert len(out) == 2

    def test_weighted_empty_lists(self):
        assert RetrieveMixin._weighted_score_fuse([], [], alpha=0.5, top_k=5) == []

    def test_weighted_tie_breaks_by_id(self):
        vector_hits = [("b", 1.0)]
        bm25_hits = [("a", 1.0)]
        out = RetrieveMixin._weighted_score_fuse(vector_hits, bm25_hits, alpha=0.5, top_k=5)
        assert out[0][0] == "a"
        assert out[1][0] == "b"


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


class _FakeItemRepo:
    def __init__(self) -> None:
        self._items = {
            "semantic": {"summary": "semantic summary", "extra": {}},
            "keyword": {"summary": "keyword summary", "extra": {}},
        }

    def list_items(self, where=None):
        return self._items

    def vector_search_items(self, query_vec, top_k, where=None, *, ranking="similarity", recency_decay_days=30.0):
        return [("semantic", 0.9), ("keyword", 0.2)]


class _FakeStore:
    def __init__(self) -> None:
        self.memory_item_repo = _FakeItemRepo()


class TestHybridFusionSelection:
    @pytest.mark.asyncio
    async def test_hybrid_defaults_to_rrf(self, monkeypatch: pytest.MonkeyPatch):
        service = MemoryService(
            database_config={"metadata_store": {"provider": "inmemory"}},
            retrieve_config={"method": "rag", "retriever": "hybrid"},
        )
        state = {
            "retrieve_item": True,
            "needs_retrieval": True,
            "proceed_to_items": True,
            "store": _FakeStore(),
            "where": {},
            "active_query": "keyword",
            "query_vector": [1.0, 0.0],
            "retriever": "hybrid",
        }

        def fake_bm25(_query: str, _pool, _top_k: int):
            return [("keyword", 5.0), ("semantic", 2.0)]

        def fake_rrf(*_ranked_lists, k=60, top_k=5):
            return [("semantic", 1.0)]

        def fail_weighted(*_args, **_kwargs):
            raise AssertionError("weighted fusion should not run by default")

        monkeypatch.setattr(service, "_bm25_score_items", fake_bm25, raising=True)
        monkeypatch.setattr(service, "_rrf_fuse", fake_rrf, raising=True)
        monkeypatch.setattr(service, "_weighted_score_fuse", fail_weighted, raising=True)

        out = await service._rag_recall_items(state, step_context=None)
        assert out["item_hits"] == [("semantic", 1.0)]

    @pytest.mark.asyncio
    async def test_hybrid_weighted_uses_weighted_fuse(self, monkeypatch: pytest.MonkeyPatch):
        service = MemoryService(
            database_config={"metadata_store": {"provider": "inmemory"}},
            retrieve_config={
                "method": "rag",
                "retriever": "hybrid",
                "fusion_strategy": "weighted",
                "weighted_alpha": 0.8,
            },
        )
        state = {
            "retrieve_item": True,
            "needs_retrieval": True,
            "proceed_to_items": True,
            "store": _FakeStore(),
            "where": {},
            "active_query": "keyword",
            "query_vector": [1.0, 0.0],
            "retriever": "hybrid",
        }

        def fake_bm25(_query: str, _pool, _top_k: int):
            return [("keyword", 5.0), ("semantic", 2.0)]

        def fail_rrf(*_args, **_kwargs):
            raise AssertionError("rrf fusion should not run for weighted hybrid")

        def fake_weighted(vector_hits, bm25_hits, *, alpha=0.5, top_k=5, normalization="minmax"):
            assert vector_hits == [("semantic", 0.9), ("keyword", 0.2)]
            assert bm25_hits == [("keyword", 5.0), ("semantic", 2.0)]
            assert alpha == 0.8
            assert normalization == "minmax"
            return [("semantic", 0.8)]

        monkeypatch.setattr(service, "_bm25_score_items", fake_bm25, raising=True)
        monkeypatch.setattr(service, "_rrf_fuse", fail_rrf, raising=True)
        monkeypatch.setattr(service, "_weighted_score_fuse", fake_weighted, raising=True)

        out = await service._rag_recall_items(state, step_context=None)
        assert out["item_hits"] == [("semantic", 0.8)]
