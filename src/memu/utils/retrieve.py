from __future__ import annotations

from typing import Literal, cast

RetrieveMethod = Literal["rag", "llm"]
RetrieveRanking = Literal["similarity", "salience"]


def normalize_retrieve_method(method: str | None, *, default: str) -> RetrieveMethod:
    """Resolve and validate the retrieval method for a single request."""

    raw_method = default if method is None else method
    if not isinstance(raw_method, str) or not raw_method.strip():
        msg = "retrieve method must be 'rag' or 'llm'"
        raise ValueError(msg)
    normalized = raw_method.strip().lower()
    if normalized not in {"rag", "llm"}:
        msg = "retrieve method must be 'rag' or 'llm'"
        raise ValueError(msg)
    return cast(RetrieveMethod, normalized)


def normalize_retrieve_ranking(ranking: str | None, *, default: str) -> RetrieveRanking:
    """Resolve and validate the item ranking strategy for a single retrieve request."""

    raw_ranking = default if ranking is None else ranking
    if not isinstance(raw_ranking, str) or not raw_ranking.strip():
        msg = "retrieve ranking must be 'similarity' or 'salience'"
        raise ValueError(msg)
    normalized = raw_ranking.strip().lower()
    if normalized not in {"similarity", "salience"}:
        msg = "retrieve ranking must be 'similarity' or 'salience'"
        raise ValueError(msg)
    return cast(RetrieveRanking, normalized)


__all__ = ["RetrieveMethod", "RetrieveRanking", "normalize_retrieve_method", "normalize_retrieve_ranking"]
