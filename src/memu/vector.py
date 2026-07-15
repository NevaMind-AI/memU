"""Backend-agnostic vector math for similarity search.

This module is intentionally storage-neutral: it holds the pure cosine
ranking helpers shared by the app retrieval layer and every database backend.
It must not import from any concrete ``memu.database.*`` backend so that the
abstraction is not inverted (a backend or the app layer depending on another
backend's internals).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import cast

import numpy as np


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9
    return float(np.dot(a, b) / denom)


def cosine_topk(
    query_vec: list[float],
    corpus: Iterable[tuple[str, list[float] | None]],
    k: int = 5,
) -> list[tuple[str, float]]:
    if k <= 0:
        return []

    # Filter out None vectors and collect valid entries
    ids: list[str] = []
    vecs: list[list[float]] = []
    for _id, vec in corpus:
        if vec is not None:
            ids.append(_id)
            vecs.append(cast(list[float], vec))

    if not vecs:
        return []

    # Vectorized computation: stack all vectors into a matrix
    q = np.array(query_vec, dtype=np.float32)
    matrix = np.array(vecs, dtype=np.float32)  # shape: (n, dim)

    # Compute all cosine similarities at once
    q_norm = np.linalg.norm(q)
    vec_norms = np.linalg.norm(matrix, axis=1)
    scores = matrix @ q / (vec_norms * q_norm + 1e-9)

    # Use argpartition for O(n) topk selection instead of O(n log n) sort
    n = len(scores)
    actual_k = min(k, n)
    if actual_k == n:
        topk_indices = np.argsort(scores)[::-1]
    else:
        # Get indices of top k elements (unordered), then sort only those
        topk_indices = np.argpartition(scores, -actual_k)[-actual_k:]
        topk_indices = topk_indices[np.argsort(scores[topk_indices])[::-1]]

    return [(ids[i], float(scores[i])) for i in topk_indices]


__all__ = ["cosine_topk"]
