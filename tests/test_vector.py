from __future__ import annotations

import math
from typing import cast

import numpy as np
import pytest

import memu.vector as vector_module
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


def test_cosine_topk_skips_empty_and_none_vectors() -> None:
    corpus = [
        ("ok", [1.0, 0.0]),
        ("empty", []),
        ("none", None),
    ]
    results = cosine_topk([1.0, 0.0], corpus, k=5)  # type: ignore[list-item]
    assert [doc_id for doc_id, _ in results] == ["ok"]


def test_cosine_topk_skips_wrong_dimension_vectors() -> None:
    # A dimension mismatch must not collapse np.array() into an object matrix;
    # the row is skipped so the remaining corpus still ranks.
    corpus = [("right", [1.0, 0.0]), ("wrong-dim", [0.1, 0.2, 0.3])]
    results = cosine_topk([1.0, 0.0], corpus, k=5)
    assert [doc_id for doc_id, _ in results] == ["right"]


def test_cosine_topk_empty_or_nonvector_query_returns_empty() -> None:
    assert cosine_topk([], _corpus(), k=2) == []
    assert cosine_topk([1.0, 0.0], [], k=2) == []


def test_cosine_topk_skips_nonfinite_rows_without_mutating_inputs() -> None:
    query = [1.0, 0.0]
    corpus = [
        ("nan", [float("nan"), 0.0]),
        ("best", [1.0, 0.0]),
        ("inf", [float("inf"), 0.0]),
        ("other", [0.0, 1.0]),
    ]
    original = repr((query, corpus))

    assert [row_id for row_id, _ in cosine_topk(query, corpus, k=1)] == ["best"]
    results = cosine_topk(query, corpus, k=4)
    assert [row_id for row_id, _ in results] == ["best", "other"]
    assert all(math.isfinite(score) for _, score in results)
    assert results[0][1] > results[1][1]
    assert repr((query, corpus)) == original


def test_cosine_topk_skips_rows_that_overflow_float32() -> None:
    # [1e39, 0.0] is finite in float64 but inf once the corpus is cast to
    # float32 for the ranking matrix; the row guard must judge the cast value,
    # or the row's NaN score would sort first.
    corpus = [("huge", [1e39, 0.0]), ("best", [1.0, 0.0]), ("other", [0.0, 1.0])]

    results = cosine_topk([1.0, 0.0], corpus, k=3)

    assert [row_id for row_id, _ in results] == ["best", "other"]
    assert all(math.isfinite(score) for _, score in results)


def test_cosine_topk_checks_corpus_finiteness_in_one_matrix_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    original_isfinite = np.isfinite
    checked_shapes: list[tuple[int, ...]] = []

    def track_isfinite(values: np.ndarray) -> np.ndarray:
        checked_shapes.append(values.shape)
        return cast(np.ndarray, original_isfinite(values))

    monkeypatch.setattr(vector_module.np, "isfinite", track_isfinite)
    corpus = [
        ("best", [1.0, 0.0]),
        ("nan", [float("nan"), 0.0]),
        ("overflow", [1e39, 0.0]),
        ("other", [0.0, 1.0]),
    ]

    assert [row_id for row_id, _ in cosine_topk([1.0, 0.0], corpus, k=4)] == ["best", "other"]
    assert checked_shapes == [(2,), (4, 2)]


def test_cosine_topk_nonfinite_query_returns_empty_without_mutating_inputs() -> None:
    corpus = _corpus()
    for value in (float("nan"), float("inf")):
        query = [value, 0.0]
        original = repr((query, corpus))
        assert cosine_topk(query, corpus, k=2) == []
        assert repr((query, corpus)) == original
