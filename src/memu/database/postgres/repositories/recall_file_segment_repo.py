from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from memu.database.models import RecallFileSegment
from memu.database.postgres.repositories.base import PostgresRepoBase
from memu.database.postgres.session import SessionManager
from memu.database.repositories.recall_file_segment import RecallFileSegmentRepo
from memu.database.state import DatabaseState


class PostgresRecallFileSegmentRepo(PostgresRepoBase, RecallFileSegmentRepo):
    def __init__(
        self,
        *,
        state: DatabaseState,
        recall_file_segment_model: type[RecallFileSegment],
        sqla_models: Any,
        sessions: SessionManager,
        scope_fields: list[str],
    ) -> None:
        super().__init__(state=state, sqla_models=sqla_models, sessions=sessions, scope_fields=scope_fields)
        self._recall_file_segment_model = recall_file_segment_model
        self.segments: list[RecallFileSegment] = self._state.segments

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

    def _cache_segment(self, row: Any) -> RecallFileSegment:
        seg = self._row_to_record(row)
        self.segments.append(seg)
        return seg

    def list_segments(self, where: Mapping[str, Any] | None = None) -> list[RecallFileSegment]:
        from sqlmodel import select

        filters = self._build_filters(self._sqla_models.RecallFileSegment, where)
        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.RecallFileSegment).where(*filters)).all()
            return [self._cache_segment(row) for row in rows]

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
        row = self._recall_file_segment_model(
            recall_file_id=recall_file_id,
            track=track,
            text=text,
            embedding=self._prepare_embedding(embedding),
            created_at=now,
            updated_at=now,
            **user_data,
        )
        with self._sessions.session() as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._cache_segment(row)

    def delete_segment(self, segment_id: str) -> None:
        from sqlmodel import delete

        with self._sessions.session() as session:
            session.exec(
                delete(self._sqla_models.RecallFileSegment).where(self._sqla_models.RecallFileSegment.id == segment_id)
            )
            session.commit()
        self.segments[:] = [seg for seg in self.segments if seg.id != segment_id]

    def delete_segments_for_file(self, recall_file_id: str) -> list[RecallFileSegment]:
        from sqlmodel import delete, select

        with self._sessions.session() as session:
            rows = session.scalars(
                select(self._sqla_models.RecallFileSegment).where(
                    self._sqla_models.RecallFileSegment.recall_file_id == recall_file_id
                )
            ).all()
            removed = [self._row_to_record(row) for row in rows]
            if removed:
                session.exec(
                    delete(self._sqla_models.RecallFileSegment).where(
                        self._sqla_models.RecallFileSegment.recall_file_id == recall_file_id
                    )
                )
                session.commit()
        self.segments[:] = [seg for seg in self.segments if seg.recall_file_id != recall_file_id]
        return removed

    def clear_segments(self, where: Mapping[str, Any] | None = None) -> list[RecallFileSegment]:
        from sqlmodel import delete, select

        filters = self._build_filters(self._sqla_models.RecallFileSegment, where)
        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.RecallFileSegment).where(*filters)).all()
            removed = [self._row_to_record(row) for row in rows]
            if removed:
                session.exec(delete(self._sqla_models.RecallFileSegment).where(*filters))
                session.commit()
        removed_ids = {seg.id for seg in removed}
        self.segments[:] = [seg for seg in self.segments if seg.id not in removed_ids]
        return removed

    def load_existing(self) -> None:
        from sqlmodel import select

        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.RecallFileSegment)).all()
            for row in rows:
                self._cache_segment(row)


__all__ = ["PostgresRecallFileSegmentRepo"]
