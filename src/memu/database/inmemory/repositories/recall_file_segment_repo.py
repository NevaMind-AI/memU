from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from memu.database.inmemory.repositories.filter import matches_where
from memu.database.inmemory.state import InMemoryState
from memu.database.models import RecallFileSegment
from memu.database.repositories.recall_file_segment import RecallFileSegmentRepo


class InMemoryFileSegmentRepository(RecallFileSegmentRepo):
    def __init__(self, *, state: InMemoryState, recall_file_segment_model: type[RecallFileSegment]) -> None:
        self._state = state
        self.recall_file_segment_model = recall_file_segment_model
        self.segments: list[RecallFileSegment] = self._state.segments

    def list_segments(self, where: Mapping[str, Any] | None = None) -> list[RecallFileSegment]:
        if not where:
            return list(self.segments)
        return [seg for seg in self.segments if matches_where(seg, where)]

    def list_segments_for_file(self, recall_file_id: str) -> list[RecallFileSegment]:
        return [seg for seg in self.segments if seg.recall_file_id == recall_file_id]

    def create_segment(
        self,
        *,
        recall_file_id: str,
        text: str,
        embedding: list[float] | None,
        user_data: dict[str, Any],
        track: str = "memory",
    ) -> RecallFileSegment:
        seg = self.recall_file_segment_model(
            id=str(uuid.uuid4()),
            recall_file_id=recall_file_id,
            track=track,
            text=text,
            embedding=embedding,
            **user_data,
        )
        self.segments.append(seg)
        return seg

    def delete_segment(self, segment_id: str) -> None:
        # Mutate the shared state list in place so the DatabaseState reference and this
        # repo's view never diverge.
        self.segments[:] = [seg for seg in self.segments if seg.id != segment_id]

    def delete_segments_for_file(self, recall_file_id: str) -> list[RecallFileSegment]:
        removed = [seg for seg in self.segments if seg.recall_file_id == recall_file_id]
        self.segments[:] = [seg for seg in self.segments if seg.recall_file_id != recall_file_id]
        return removed

    def clear_segments(self, where: Mapping[str, Any] | None = None) -> list[RecallFileSegment]:
        if not where:
            removed = list(self.segments)
            self.segments.clear()
            return removed
        removed = [seg for seg in self.segments if matches_where(seg, where)]
        removed_ids = {seg.id for seg in removed}
        self.segments[:] = [seg for seg in self.segments if seg.id not in removed_ids]
        return removed

    def load_existing(self) -> None:
        return None


__all__ = ["InMemoryFileSegmentRepository"]
