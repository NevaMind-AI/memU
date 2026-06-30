"""SQLite file-segment repository implementation."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from sqlmodel import delete, select

from memu.database.models import RecallFileSegment
from memu.database.repositories.recall_file_segment import RecallFileSegmentRepo
from memu.database.sqlite.repositories.base import SQLiteRepoBase
from memu.database.sqlite.schema import SQLiteSQLAModels
from memu.database.sqlite.session import SQLiteSessionManager
from memu.database.state import DatabaseState
from memu.vector import cosine_topk

logger = logging.getLogger(__name__)


class SQLiteRecallFileSegmentRepo(SQLiteRepoBase, RecallFileSegmentRepo):
    """SQLite implementation of the file-segment repository."""

    def __init__(
        self,
        *,
        state: DatabaseState,
        recall_file_segment_model: type[Any],
        sqla_models: SQLiteSQLAModels,
        sessions: SQLiteSessionManager,
        scope_fields: list[str],
    ) -> None:
        super().__init__(
            state=state,
            sqla_models=sqla_models,
            sessions=sessions,
            scope_fields=scope_fields,
        )
        self._recall_file_segment_model = recall_file_segment_model
        self.segments = self._state.segments

    def _row_to_record(self, row: Any) -> RecallFileSegment:
        return RecallFileSegment(
            id=row.id,
            recall_file_id=row.recall_file_id,
            track=row.track,
            text=row.text,
            embedding=self._normalize_embedding(row.embedding),
            created_at=row.created_at,
            updated_at=row.updated_at,
            **self._scope_kwargs_from(row),
        )

    def list_segments(self, where: Mapping[str, Any] | None = None) -> list[RecallFileSegment]:
        with self._sessions.session() as session:
            stmt = select(self._recall_file_segment_model)
            filters = self._build_filters(self._recall_file_segment_model, where)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.exec(stmt).all()

        result: list[RecallFileSegment] = []
        for row in rows:
            seg = self._row_to_record(row)
            result.append(seg)
            if not any(s.id == seg.id for s in self.segments):
                self.segments.append(seg)
        return result

    def list_segments_for_file(self, recall_file_id: str) -> list[RecallFileSegment]:
        return self.list_segments({"recall_file_id": recall_file_id})

    def create_segment(
        self,
        *,
        recall_file_id: str,
        text: str,
        embedding: list[float] | None,
        user_data: dict[str, Any],
        track: str = "memory",
    ) -> RecallFileSegment:
        now = self._now()
        with self._sessions.session() as session:
            row = self._recall_file_segment_model(
                recall_file_id=recall_file_id,
                track=track,
                text=text,
                embedding=self._prepare_embedding(embedding),
                created_at=now,
                updated_at=now,
                **user_data,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            seg = self._row_to_record(row)

        self.segments.append(seg)
        return seg

    def delete_segment(self, segment_id: str) -> None:
        with self._sessions.session() as session:
            session.exec(
                delete(self._recall_file_segment_model).where(self._recall_file_segment_model.id == segment_id)
            )
            session.commit()
        self.segments[:] = [seg for seg in self.segments if seg.id != segment_id]

    def delete_segments_for_file(self, recall_file_id: str) -> list[RecallFileSegment]:
        removed = self.list_segments_for_file(recall_file_id)
        if not removed:
            return []
        with self._sessions.session() as session:
            session.exec(
                delete(self._recall_file_segment_model).where(
                    self._recall_file_segment_model.recall_file_id == recall_file_id
                )
            )
            session.commit()
        self.segments[:] = [seg for seg in self.segments if seg.recall_file_id != recall_file_id]
        return removed

    def clear_segments(self, where: Mapping[str, Any] | None = None) -> list[RecallFileSegment]:
        removed = self.list_segments(where)
        if not removed:
            return []
        filters = self._build_filters(self._recall_file_segment_model, where)
        with self._sessions.session() as session:
            del_stmt = delete(self._recall_file_segment_model)
            if filters:
                del_stmt = del_stmt.where(*filters)
            session.exec(del_stmt)
            session.commit()
        removed_ids = {seg.id for seg in removed}
        self.segments[:] = [seg for seg in self.segments if seg.id not in removed_ids]
        return removed

    def vector_search_segments(
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        pool = self.list_segments(where)
        return cosine_topk(query_vec, [(seg.id, seg.embedding) for seg in pool], k=top_k)

    def load_existing(self) -> None:
        self.list_segments()


__all__ = ["SQLiteRecallFileSegmentRepo"]
