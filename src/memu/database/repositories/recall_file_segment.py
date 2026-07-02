from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from memu.database.models import RecallFileSegment


@runtime_checkable
class RecallFileSegmentRepo(Protocol):
    """Repository contract for file segments (searchable L2 slices of a ``RecallFile``)."""

    segments: list[RecallFileSegment]

    def list_segments(self, where: Mapping[str, Any] | None = None) -> list[RecallFileSegment]: ...

    def list_segments_for_file(self, recall_file_id: str) -> list[RecallFileSegment]:
        """Return all segments belonging to a given file."""
        ...

    def create_segment(
        self, *, recall_file_id: str, text: str, embedding: list[float] | None, user_data: dict[str, Any]
    ) -> RecallFileSegment: ...

    def delete_segment(self, segment_id: str) -> None: ...

    def delete_segments_for_file(self, recall_file_id: str) -> list[RecallFileSegment]:
        """Remove all segments for a given file. Returns the removed segments."""
        ...

    def clear_segments(self, where: Mapping[str, Any] | None = None) -> list[RecallFileSegment]:
        """Remove all segments matching the scope. Returns the removed segments."""
        ...

    def load_existing(self) -> None: ...
