"""Storage-neutral hybrid ranking: BM25 + cosine fused with RRF.

Used by every retrieve backend. Cosine itself stays in :mod:`memu.vector`;
this module only tokenizes, scores BM25, and fuses two ranked id lists.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from itertools import pairwise

RRF_K = 60
BM25_K1 = 1.5
BM25_B = 0.75

# Latin/digit runs stay whole tokens. CJK/kana/hangul runs are split into
# overlapping character n-grams below (unigrams + bigrams).
_TOKEN_RE = re.compile(
    r"[a-z0-9]+|[\u3400-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]+",
    re.IGNORECASE,
)


def hybrid_candidate_k(top_k: int) -> int:
    """How many hits each ranker contributes before RRF on an indexed backend."""
    return max(50, 5 * top_k)


def tokenize(text: str) -> list[str]:
    """Lowercased latin tokens plus CJK unigrams and bigrams."""
    if not text:
        return []
    out: list[str] = []
    for match in _TOKEN_RE.finditer(text):
        token = match.group()
        if token.isascii():
            out.append(token.lower())
            continue
        chars = list(token)
        out.extend(chars)
        out.extend(a + b for a, b in pairwise(chars))
    return out


def bm25_rank(
    query: str,
    corpus: Sequence[tuple[str, str]],
    *,
    k: int | None = None,
) -> list[tuple[str, float]]:
    """Return ``(id, bm25)`` pairs, best first, dropping zero-score docs.

    Empty query tokens or an empty tokenized corpus yield ``[]``.
    """
    documents = [(doc_id, tokenize(text)) for doc_id, text in corpus]
    documents = [(doc_id, tokens) for doc_id, tokens in documents if tokens]
    query_tokens = tokenize(query)
    if not documents or not query_tokens:
        return []

    n = len(documents)
    df: dict[str, int] = {}
    for _, tokens in documents:
        for term in set(tokens):
            df[term] = df.get(term, 0) + 1
    avgdl = sum(len(tokens) for _, tokens in documents) / n

    scores: dict[str, float] = {}
    for doc_id, tokens in documents:
        tf: dict[str, int] = {}
        for term in tokens:
            tf[term] = tf.get(term, 0) + 1
        dl = len(tokens)
        score = 0.0
        for term in query_tokens:
            freq = tf.get(term)
            if not freq:
                continue
            idf = math.log((n - df[term] + 0.5) / (df[term] + 0.5) + 1.0)
            denom = freq + BM25_K1 * (1.0 - BM25_B + BM25_B * dl / avgdl)
            score += idf * (freq * (BM25_K1 + 1.0)) / denom
        if score > 0.0:
            scores[doc_id] = score

    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    if k is not None:
        ordered = ordered[:k]
    return ordered


def rrf_topk(*rankings: Sequence[str], top_k: int, rrf_k: int = RRF_K) -> list[tuple[str, float]]:
    """Fuse best-first id lists with Reciprocal Rank Fusion; cut to ``top_k``."""
    if top_k <= 0:
        return []
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (rrf_k + rank)
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return ordered[:top_k]


def maybe_hybrid_topk(
    *,
    query_text: str | None,
    cosine_hits: Sequence[tuple[str, float]],
    texts: Mapping[str, str],
    top_k: int,
    bm25_limit: int | None = None,
) -> list[tuple[str, float]]:
    """RRF-fuse cosine and BM25 when the query tokenizes; else keep cosine.

    ``cosine_hits`` is already best-first (full pool or a truncated candidate
    list). BM25 runs over ``texts``, so a keyword hit missing from the cosine
    list can still enter the union. Falls back to cosine scores when BM25
    produces no ranking, so ``query_text=None`` is bit-identical to today's
    cosine-only retrieve.
    """
    if top_k <= 0:
        return []
    cosine_ids = [doc_id for doc_id, _ in cosine_hits]
    if not query_text or not query_text.strip() or not tokenize(query_text):
        return list(cosine_hits[:top_k])

    corpus = [(doc_id, text) for doc_id, text in texts.items() if text and text.strip()]
    bm25_hits = bm25_rank(query_text, corpus, k=bm25_limit)
    if not bm25_hits:
        return list(cosine_hits[:top_k])
    return rrf_topk(cosine_ids, [doc_id for doc_id, _ in bm25_hits], top_k=top_k)


__all__ = [
    "RRF_K",
    "bm25_rank",
    "hybrid_candidate_k",
    "maybe_hybrid_topk",
    "rrf_topk",
    "tokenize",
]
