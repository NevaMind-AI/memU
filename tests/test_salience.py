"""
Tests for salience-aware memory features:
- Memory deduplication via content hash
- Reinforcement tracking
- Salience-aware retrieval ranking
"""

from __future__ import annotations

import hashlib
import math
from datetime import UTC, datetime, timedelta


# Inline implementations to avoid circular import issues during testing
def compute_content_hash(summary: str, memory_type: str) -> str:
    """Generate unique hash for memory deduplication."""
    normalized = " ".join(summary.lower().split())
    content = f"{memory_type}:{normalized}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def salience_score(
    similarity: float,
    reinforcement_count: int,
    last_reinforced_at: datetime | None,
    recency_decay_days: float = 30.0,
) -> float:
    """Compute salience-aware score combining similarity, reinforcement, and recency."""
    reinforcement_factor = math.log(reinforcement_count + 1)

    if last_reinforced_at is None:
        recency_factor = 0.5
    else:
        now = datetime.now(last_reinforced_at.tzinfo) if last_reinforced_at.tzinfo else datetime.now(UTC)
        days_ago = (now - last_reinforced_at).total_seconds() / 86400
        recency_factor = math.exp(-0.693 * days_ago / recency_decay_days)

    return similarity * reinforcement_factor * recency_factor


def _cosine(a: list[float], b: list[float]) -> float:
    import numpy as np

    a_arr = np.array(a, dtype=np.float32)
    b_arr = np.array(b, dtype=np.float32)
    denom = (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)) + 1e-9
    return float(np.dot(a_arr, b_arr) / denom)


def cosine_topk_salience(
    query_vec: list[float],
    corpus: list[tuple[str, list[float] | None, int, datetime | None]],
    k: int = 5,
    recency_decay_days: float = 30.0,
) -> list[tuple[str, float]]:
    """Top-k retrieval using salience-aware scoring."""
    scored: list[tuple[str, float]] = []

    for _id, vec, reinforcement_count, last_reinforced_at in corpus:
        if vec is None:
            continue
        similarity = _cosine(query_vec, vec)
        score = salience_score(similarity, reinforcement_count, last_reinforced_at, recency_decay_days)
        scored.append((_id, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


class TestContentHash:
    """Tests for content hash computation."""

    def test_basic_hash(self):
        """Hash should be deterministic."""
        hash1 = compute_content_hash("User loves coffee", "profile")
        hash2 = compute_content_hash("User loves coffee", "profile")
        assert hash1 == hash2
        assert len(hash1) == 16  # 16 hex chars

    def test_different_content_different_hash(self):
        """Different content should produce different hashes."""
        hash1 = compute_content_hash("User loves coffee", "profile")
        hash2 = compute_content_hash("User loves tea", "profile")
        assert hash1 != hash2

    def test_different_type_different_hash(self):
        """Same content with different type should produce different hashes."""
        hash1 = compute_content_hash("User loves coffee", "profile")
        hash2 = compute_content_hash("User loves coffee", "event")
        assert hash1 != hash2

    def test_whitespace_normalization(self):
        """Whitespace variations should produce same hash."""
        hash1 = compute_content_hash("User loves coffee", "profile")
        hash2 = compute_content_hash("User  loves   coffee", "profile")
        hash3 = compute_content_hash("  User loves coffee  ", "profile")
        assert hash1 == hash2 == hash3

    def test_case_insensitive(self):
        """Hash should be case-insensitive."""
        hash1 = compute_content_hash("User loves coffee", "profile")
        hash2 = compute_content_hash("USER LOVES COFFEE", "profile")
        assert hash1 == hash2


class TestSalienceScore:
    """Tests for salience score computation."""

    def test_basic_salience(self):
        """Basic salience score should be positive."""
        score = salience_score(
            similarity=0.8,
            reinforcement_count=1,
            last_reinforced_at=datetime.now(UTC),
            recency_decay_days=30.0,
        )
        assert score > 0

    def test_higher_reinforcement_higher_score(self):
        """Higher reinforcement count should increase score."""
        now = datetime.now(UTC)
        score_low = salience_score(0.8, 1, now, 30.0)
        score_high = salience_score(0.8, 10, now, 30.0)
        assert score_high > score_low

    def test_recent_memory_higher_score(self):
        """More recent memories should score higher."""
        now = datetime.now(UTC)
        old = now - timedelta(days=60)

        score_recent = salience_score(0.8, 1, now, 30.0)
        score_old = salience_score(0.8, 1, old, 30.0)
        assert score_recent > score_old

    def test_none_last_reinforced_neutral(self):
        """None last_reinforced_at should give neutral recency factor."""
        score = salience_score(0.8, 1, None, 30.0)
        # With recency_factor=0.5 and reinforcement_factor=log(2)≈0.69
        # score ≈ 0.8 * 0.69 * 0.5 ≈ 0.28
        assert 0.2 < score < 0.4

    def test_reinforcement_vs_recency_tradeoff(self):
        """High reinforcement old memory vs low reinforcement recent memory."""
        now = datetime.now(UTC)
        old = now - timedelta(days=30)  # 30 days ago = half-life

        # Memory A: high reinforcement (10), old (30 days)
        score_a = salience_score(0.85, 10, old, 30.0)

        # Memory B: low reinforcement (1), recent (now)
        score_b = salience_score(0.85, 1, now, 30.0)

        # A should score higher due to reinforcement
        # A: 0.85 * log(11) * 0.5 ≈ 0.85 * 2.4 * 0.5 ≈ 1.02
        # B: 0.85 * log(2) * 1.0 ≈ 0.85 * 0.69 * 1.0 ≈ 0.59
        assert score_a > score_b


class TestCosineTopkSalience:
    """Tests for salience-aware top-k retrieval."""

    def test_basic_retrieval(self) -> None:
        """Should return top-k results sorted by salience."""
        query = [1.0, 0.0, 0.0]
        now = datetime.now(UTC)

        corpus: list[tuple[str, list[float] | None, int, datetime | None]] = [
            ("id1", [1.0, 0.0, 0.0], 1, now),  # Perfect match, low reinforcement
            ("id2", [0.9, 0.1, 0.0], 10, now),  # Good match, high reinforcement
            ("id3", [0.5, 0.5, 0.0], 1, now),  # Weak match
        ]

        results = cosine_topk_salience(query, corpus, k=2, recency_decay_days=30.0)

        assert len(results) == 2
        # id2 should rank first due to high reinforcement despite slightly lower similarity
        assert results[0][0] == "id2"

    def test_skips_none_embeddings(self) -> None:
        """Should skip items with None embeddings."""
        query = [1.0, 0.0, 0.0]
        now = datetime.now(UTC)

        corpus: list[tuple[str, list[float] | None, int, datetime | None]] = [
            ("id1", [1.0, 0.0, 0.0], 1, now),
            ("id2", None, 10, now),  # None embedding
        ]

        results = cosine_topk_salience(query, corpus, k=5, recency_decay_days=30.0)

        assert len(results) == 1
        assert results[0][0] == "id1"

    def test_respects_k_limit(self) -> None:
        """Should return at most k results."""
        query = [1.0, 0.0, 0.0]
        now = datetime.now(UTC)

        corpus: list[tuple[str, list[float] | None, int, datetime | None]] = [
            ("id1", [1.0, 0.0, 0.0], 1, now),
            ("id2", [0.9, 0.1, 0.0], 1, now),
            ("id3", [0.8, 0.2, 0.0], 1, now),
            ("id4", [0.7, 0.3, 0.0], 1, now),
        ]

        results = cosine_topk_salience(query, corpus, k=2, recency_decay_days=30.0)

        assert len(results) == 2
