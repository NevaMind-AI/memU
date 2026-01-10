from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import datetime
from typing import cast

import numpy as np


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9
    return float(np.dot(a, b) / denom)


def salience_score(
    similarity: float,
    reinforcement_count: int,
    last_reinforced_at: datetime | None,
    recency_decay_days: float = 30.0,
) -> float:
    """
    Compute salience-aware score combining similarity, reinforcement, and recency.

    Formula: similarity × reinforcement_factor × recency_factor

    - reinforcement_factor: log(count + 1) to dampen extreme counts
      (Logarithmic scaling prevents runaway dominance by frequently repeated facts)
    - recency_factor: exponential decay based on days since last reinforcement
      (Uses half-life decay: after recency_decay_days, factor is ~0.5)

    Args:
        similarity: Cosine similarity score (0 to 1)
        reinforcement_count: Number of times this memory was reinforced
        last_reinforced_at: When the memory was last reinforced
        recency_decay_days: Half-life for recency decay in days

    Returns:
        Salience score (higher = more salient)
    """
    # Reinforcement factor (logarithmic to prevent runaway scores)
    reinforcement_factor = math.log(reinforcement_count + 1)

    # Recency factor (exponential decay with half-life)
    if last_reinforced_at is None:
        recency_factor = 0.5  # Unknown recency gets neutral score
    else:
        now = datetime.now(last_reinforced_at.tzinfo) if last_reinforced_at.tzinfo else datetime.utcnow()
        days_ago = (now - last_reinforced_at).total_seconds() / 86400
        # 0.693 = ln(2), gives us proper half-life decay
        recency_factor = math.exp(-0.693 * days_ago / recency_decay_days)

    return similarity * reinforcement_factor * recency_factor


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


def cosine_topk_salience(
    query_vec: list[float],
    corpus: Iterable[tuple[str, list[float] | None, int, datetime | None]],
    k: int = 5,
    recency_decay_days: float = 30.0,
) -> list[tuple[str, float]]:
    """
    Top-k retrieval using salience-aware scoring.

    Ranks memories by: similarity × log(reinforcement+1) × recency_decay

    Args:
        query_vec: Query embedding vector
        corpus: Iterable of (id, embedding, reinforcement_count, last_reinforced_at)
        k: Number of top results to return
        recency_decay_days: Half-life for recency decay

    Returns:
        List of (id, salience_score) tuples, sorted by score descending
    """
    q = np.array(query_vec, dtype=np.float32)
    scored: list[tuple[str, float]] = []

    for _id, vec, reinforcement_count, last_reinforced_at in corpus:
        if vec is None:
            continue
        vec_list = cast(list[float], vec)
        v = np.array(vec_list, dtype=np.float32)
        similarity = _cosine(q, v)
        score = salience_score(similarity, reinforcement_count, last_reinforced_at, recency_decay_days)
        scored.append((_id, score))

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
