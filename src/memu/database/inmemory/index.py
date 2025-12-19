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
    q = np.array(query_vec, dtype=np.float32)
    scored: list[tuple[str, float]] = []
    for _id, vec in corpus:
        if vec is None:
            continue
        vec_list = cast(list[float], vec)
        v = np.array(vec_list, dtype=np.float32)
        scored.append((_id, _cosine(q, v)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


def query_cosine(query_vec: list[float], vecs: list[list[float]]) -> list[tuple[int, float]]:
    res: list[tuple[int, float]] = []
    q = np.array(query_vec, dtype=np.float32)
    for i, v in enumerate(vecs):
        vec_array = np.array(v, dtype=np.float32)
        res.append((i, _cosine(q, vec_array)))
    res.sort(key=lambda x: x[1], reverse=True)
    return res
