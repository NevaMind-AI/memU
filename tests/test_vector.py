from __future__ import annotations

import pytest

from memu.database.inmemory.vector import cosine_topk


def _corpus() -> list[tuple[str, list[float]]]:
    return [("a", [1.0, 0.0]), ("b", [0.0, 1.0]), ("c", [0.7, 0.7])]


def test_cosine_topk_nonpositive_k_returns_empty() -> None:
    # top_k <= 0 must return nothing, not the entire corpus (which is what the
    # argpartition path did for k == 0).
    assert cosine_topk([1.0, 0.0], _corpus(), k=0) == []
    assert cosine_topk([1.0, 0.0], _corpus(), k=-1) == []


def test_cosine_topk_orders_by_similarity() -> None:
    results = cosine_topk([1.0, 0.0], _corpus(), k=2)
    assert [memory_id for memory_id, _ in results] == ["a", "c"]


def test_cosine_topk_rejects_embedding_dimension_mismatch() -> None:
    corpus = [("valid", [1.0, 0.0, 0.0]), ("invalid", [1.0, 0.0])]

    with pytest.raises(
        ValueError,
        match=r"invalid.*query has 3 dimensions.*stored vector has 2",
    ):
        cosine_topk([1.0, 0.0, 0.0], corpus)
