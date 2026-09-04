from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from memu.database.models import RecallFileSegment
from memu.hybrid import maybe_hybrid_topk
from memu.vector import cosine_topk


@runtime_checkable
class RecallFileSegmentRepo(Protocol):
    """Repository contract for file segments (searchable L2 slices of a ``RecallFile``)."""

    segments: list[RecallFileSegment]

    def list_segments(self, where: Mapping[str, Any] | None = None) -> list[RecallFileSegment]: ...

    def vector_search_segments(
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
        *,
        query_text: str | None = None,
    ) -> list[tuple[RecallFileSegment, float]]:
        """Rank segments by cosine, optionally fused with BM25 over ``text``.

        Returns ``(segment, score)`` pairs ordered by descending score, at most
        ``top_k`` of them. ``query_text=None`` is cosine-only (today's contract).
        With ``query_text``, this default scores the whole scoped pool — sqlite
        and inmemory already scan it — then RRF-fuses BM25 (ADR 0019).

        The segments themselves come back, not their ids.

        A backend whose store can rank natively should override it, and may
        call back here via ``super()`` when its index is unavailable.
        """
        pool = self.list_segments(where)
        by_id = {seg.id: seg for seg in pool}
        cosine_k = len(pool) if query_text and query_text.strip() else top_k
        ranked = cosine_topk(query_vec, [(seg.id, seg.embedding) for seg in pool], k=cosine_k)
        fused = maybe_hybrid_topk(
            query_text=query_text,
            cosine_hits=ranked,
            texts={seg.id: seg.text for seg in pool},
            top_k=top_k,
        )
        return [(by_id[seg_id], score) for seg_id, score in fused if seg_id in by_id]

    def list_segments_for_file(self, recall_file_id: str) -> list[RecallFileSegment]:
        """Return all segments belonging to a given file."""
        ...

    def create_segment(
        self,
        *,
        recall_file_id: str,
        text: str,
        embedding: list[float] | None,
        user_data: dict[str, Any],
        track: str = "memory",
    ) -> RecallFileSegment: ...

    def delete_segment(self, segment_id: str) -> None: ...

    def delete_segments_for_file(self, recall_file_id: str) -> list[RecallFileSegment]:
        """Remove all segments for a given file. Returns the removed segments."""
        ...

    def clear_segments(self, where: Mapping[str, Any] | None = None) -> list[RecallFileSegment]:
        """Remove all segments matching the scope. Returns the removed segments."""
        ...

    def load_existing(self) -> None: ...
