from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from memu.database.inmemory.repositories.filter import matches_where
from memu.database.inmemory.state import InMemoryState
from memu.database.models import RecallFileSegment
from memu.database.repositories.recall_file_segment import RecallFileSegmentRepo
from memu.database.vector_index.interfaces import VectorIndex
from memu.vector import cosine_topk


class InMemoryFileSegmentRepository(RecallFileSegmentRepo):
    def __init__(
        self,
        *,
        state: InMemoryState,
        recall_file_segment_model: type[RecallFileSegment],
        vector_index: VectorIndex | None = None,
    ) -> None:
        self._state = state
        self.recall_file_segment_model = recall_file_segment_model
        self.segments: list[RecallFileSegment] = self._state.segments
        self._vector_index = vector_index

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
        if self._vector_index is not None and embedding:
            self._vector_index.upsert(
                seg.id,
                embedding,
                scope={"recall_file_id": recall_file_id, "track": track, **user_data},
            )
        return seg

    def delete_segment(self, segment_id: str) -> None:
        # Mutate the shared state list in place so the DatabaseState reference and this
        # repo's view never diverge.
        self.segments[:] = [seg for seg in self.segments if seg.id != segment_id]
        if self._vector_index is not None:
            self._vector_index.delete(segment_id)

    def delete_segments_for_file(self, recall_file_id: str) -> list[RecallFileSegment]:
        removed = [seg for seg in self.segments if seg.recall_file_id == recall_file_id]
        self.segments[:] = [seg for seg in self.segments if seg.recall_file_id != recall_file_id]
        if self._vector_index is not None:
            self._vector_index.delete_many(seg.id for seg in removed)
        return removed

    def clear_segments(self, where: Mapping[str, Any] | None = None) -> list[RecallFileSegment]:
        if not where:
            removed = list(self.segments)
            self.segments.clear()
            if self._vector_index is not None:
                self._vector_index.delete_many(seg.id for seg in removed)
            return removed
        removed = [seg for seg in self.segments if matches_where(seg, where)]
        removed_ids = {seg.id for seg in removed}
        self.segments[:] = [seg for seg in self.segments if seg.id not in removed_ids]
        if self._vector_index is not None:
            self._vector_index.delete_many(removed_ids)
        return removed

    def vector_search_segments(
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        if self._vector_index is not None:
            return self._vector_index.search(query_vec, top_k, where=where)
        pool = self.list_segments(where)
        return cosine_topk(query_vec, [(seg.id, seg.embedding) for seg in pool], k=top_k)

    def load_existing(self) -> None:
        return None


__all__ = ["InMemoryFileSegmentRepository"]
