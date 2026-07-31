from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from memu.database.models import RecallFile
from memu.database.postgres.repositories.base import PostgresRepoBase
from memu.database.postgres.session import SessionManager
from memu.database.repositories.recall_file import RecallFileRepo
from memu.database.state import DatabaseState


class PostgresRecallFileRepo(PostgresRepoBase, RecallFileRepo):
    def __init__(
        self,
        *,
        state: DatabaseState,
        recall_file_model: type[RecallFile],
        sqla_models: Any,
        sessions: SessionManager,
        scope_fields: list[str],
    ) -> None:
        super().__init__(state=state, sqla_models=sqla_models, sessions=sessions, scope_fields=scope_fields)
        self._recall_file_model = recall_file_model
        self.recall_files: dict[str, RecallFile] = self._state.recall_files

    def list_recall_files(self, where: Mapping[str, Any] | None = None) -> dict[str, RecallFile]:
        from sqlmodel import select

        filters = self._build_filters(self._sqla_models.RecallFile, where)
        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.RecallFile).where(*filters)).all()
            result: dict[str, RecallFile] = {}
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                recall_file = self._cache_recall_file(row)
                result[recall_file.id] = recall_file
        return result

    def list_recall_files_page(
        self,
        where: Mapping[str, Any] | None,
        *,
        after: tuple[str, str, str] | None,
        limit: int,
    ) -> tuple[list[RecallFile], tuple[str, str, str] | None]:
        """One keyset page ordered by ``(track, name, id)`` (ADR 0014)."""
        from sqlalchemy import tuple_
        from sqlmodel import select

        model = self._sqla_models.RecallFile
        filters = self._build_filters(model, where)
        with self._sessions.session() as session:
            stmt = select(model).where(*filters)
            if after is not None:
                # Row-value keyset: resume strictly after the last row seen.
                stmt = stmt.where(tuple_(model.track, model.name, model.id) > after)
            # One extra row reveals whether a further page exists; trimmed below.
            stmt = stmt.order_by(model.track, model.name, model.id).limit(limit + 1)
            rows = session.scalars(stmt).all()
            has_more = len(rows) > limit
            rows = rows[:limit]
            files: list[RecallFile] = []
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                files.append(self._cache_recall_file(row))
        next_after = (files[-1].track, files[-1].name, files[-1].id) if has_more else None
        return files, next_after

    def clear_recall_files(self, where: Mapping[str, Any] | None = None) -> dict[str, RecallFile]:
        from sqlmodel import delete, select

        filters = self._build_filters(self._sqla_models.RecallFile, where)
        with self._sessions.session() as session:
            # First get the objects to delete
            rows = session.scalars(select(self._sqla_models.RecallFile).where(*filters)).all()
            deleted: dict[str, RecallFile] = {}
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                deleted[row.id] = row

            if not deleted:
                return {}

            # Delete from database
            session.exec(delete(self._sqla_models.RecallFile).where(*filters))
            session.commit()

            # Clean up cache
            for recall_file_id in deleted:
                self.recall_files.pop(recall_file_id, None)

        return deleted

    def get_or_create_recall_file(
        self,
        *,
        name: str,
        description: str,
        embedding: list[float],
        user_data: dict[str, Any],
        track: str = "memory",
    ) -> RecallFile:
        from sqlmodel import select

        now = self._now()
        with self._sessions.session() as session:
            filters = [
                self._sqla_models.RecallFile.name == name,
                self._sqla_models.RecallFile.track == track,
            ]
            for key, value in user_data.items():
                filters.append(getattr(self._sqla_models.RecallFile, key) == value)
            existing = session.scalar(select(self._sqla_models.RecallFile).where(*filters))

            if existing:
                # A stub can be empty rather than NULL: ``description`` is NOT NULL so it
                # stubs as "", and an embedding may round-trip as []. Test both falsy —
                # an ``is None`` check never fires for the former. Writes are guarded on
                # the incoming value so no-op calls leave updated_at alone, which also
                # keeps an empty embedding from ever reaching the vector column.
                updated = False
                if embedding and not self._normalize_embedding(getattr(existing, "embedding", None)):
                    existing.embedding = self._prepare_embedding(embedding)
                    updated = True
                if description and not getattr(existing, "description", ""):
                    existing.description = description
                    updated = True
                if updated:
                    existing.updated_at = now
                    session.add(existing)
                    session.commit()
                    session.refresh(existing)
                return self._cache_recall_file(existing)

            recall_file = self._recall_file_model(
                name=name,
                description=description,
                embedding=self._prepare_embedding(embedding),
                track=track,
                created_at=now,
                updated_at=now,
                **user_data,
            )
            session.add(recall_file)
            session.commit()
            session.refresh(recall_file)

        return self._cache_recall_file(recall_file)

    def update_recall_file(
        self,
        *,
        recall_file_id: str,
        name: str | None = None,
        description: str | None = None,
        embedding: list[float] | None = None,
        content: str | None = None,
    ) -> RecallFile:
        from sqlmodel import select

        now = self._now()
        with self._sessions.session() as session:
            recall_file = session.scalar(
                select(self._sqla_models.RecallFile).where(self._sqla_models.RecallFile.id == recall_file_id)
            )
            if recall_file is None:
                msg = f"RecallFile with id {recall_file_id} not found"
                raise KeyError(msg)

            if name is not None:
                recall_file.name = name
            if description is not None:
                recall_file.description = description
            if embedding is not None:
                recall_file.embedding = self._prepare_embedding(embedding)
            if content is not None:
                recall_file.content = content

            recall_file.updated_at = now
            session.add(recall_file)
            session.commit()
            session.refresh(recall_file)
            recall_file.embedding = self._normalize_embedding(recall_file.embedding)

        return self._cache_recall_file(recall_file)

    def load_existing(self) -> None:
        from sqlmodel import select

        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.RecallFile)).all()
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                self._cache_recall_file(row)

    def _cache_recall_file(self, recall_file: RecallFile) -> RecallFile:
        self.recall_files[recall_file.id] = recall_file
        return recall_file


__all__ = ["PostgresRecallFileRepo"]
