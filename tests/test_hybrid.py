"""BM25 + RRF fusion used by retrieve (ADR 0019)."""

from __future__ import annotations

from memu.hybrid import bm25_rank, hybrid_candidate_k, maybe_hybrid_topk, rrf_topk, tokenize


def test_tokenize_latin_and_cjk_ngrams() -> None:
    assert tokenize("ECONNREFUSED 5432") == ["econnrefused", "5432"]
    tokens = tokenize("武汉大学")
    assert "武" in tokens
    assert "汉" in tokens
    assert "武汉" in tokens
    assert "大学" in tokens


def test_bm25_ranks_the_document_that_has_the_rare_term() -> None:
    ranked = bm25_rank(
        "ECONNREFUSED 5432",
        [
            ("semantic", "the database timed out again"),
            ("keyword", "ECONNREFUSED 127.0.0.1:5432"),
        ],
    )
    assert next(doc_id for doc_id, _ in ranked) == "keyword"


def test_cjk_query_hits_character_ngrams() -> None:
    ranked = bm25_rank("武汉", [("en", "hello world"), ("zh", "我在武汉大学")])
    assert next(doc_id for doc_id, _ in ranked) == "zh"


def test_rrf_prefers_the_doc_strong_in_both_lists() -> None:
    # a is cosine #1 only; b is cosine #2 and BM25 #1.
    fused = rrf_topk(["a", "b"], ["b"], top_k=2)
    assert fused[0][0] == "b"


def test_hybrid_surfaces_keyword_hit_cosine_ranked_out() -> None:
    # Query vector is aligned with "close"; the rare token lives on "far".
    hits = maybe_hybrid_topk(
        query_text="ECONNREFUSED5432",
        cosine_hits=[("close", 0.99), ("far", 0.01)],
        texts={"close": "unrelated prose about weather", "far": "ECONNREFUSED5432 on boot"},
        top_k=1,
    )
    assert hits[0][0] == "far"


def test_hybrid_without_query_text_keeps_cosine_order_and_scores() -> None:
    cosine = [("close", 0.99), ("far", 0.01)]
    assert maybe_hybrid_topk(query_text=None, cosine_hits=cosine, texts={}, top_k=2) == cosine
    assert maybe_hybrid_topk(query_text="   ", cosine_hits=cosine, texts={}, top_k=1) == cosine[:1]


def test_hybrid_can_introduce_a_bm25_only_id() -> None:
    hits = maybe_hybrid_topk(
        query_text="token",
        cosine_hits=[("close", 0.99)],
        texts={"close": "unrelated", "only_bm25": "token lives here"},
        top_k=2,
        bm25_limit=2,
    )
    ids = [doc_id for doc_id, _ in hits]
    assert "only_bm25" in ids


def test_candidate_k_widens_with_top_k() -> None:
    assert hybrid_candidate_k(5) == 50
    assert hybrid_candidate_k(20) == 100
