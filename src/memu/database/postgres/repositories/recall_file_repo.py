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
        self.categories: dict[str, RecallFile] = self._state.categories

    def list_categories(self, where: Mapping[str, Any] | None = None) -> dict[str, RecallFile]:
        from sqlmodel import select

        filters = self._build_filters(self._sqla_models.RecallFile, where)
        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.RecallFile).where(*filters)).all()
            result: dict[str, RecallFile] = {}
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                cat = self._cache_category(row)
                result[cat.id] = cat
        return result

    def clear_categories(self, where: Mapping[str, Any] | None = None) -> dict[str, RecallFile]:
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
            for cat_id in deleted:
                self.categories.pop(cat_id, None)

        return deleted

    def get_or_create_category(
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
                updated = False
                if getattr(existing, "embedding", None) is None:
                    existing.embedding = self._prepare_embedding(embedding)
                    updated = True
                if getattr(existing, "description", None) is None:
                    existing.description = description
                    updated = True
                if updated:
                    existing.updated_at = now
                    session.add(existing)
                    session.commit()
                    session.refresh(existing)
                return self._cache_category(existing)

            cat = self._recall_file_model(
                name=name,
                description=description,
                embedding=self._prepare_embedding(embedding),
                track=track,
                created_at=now,
                updated_at=now,
                **user_data,
            )
            session.add(cat)
            session.commit()
            session.refresh(cat)

        return self._cache_category(cat)

    def update_category(
        self,
        *,
        category_id: str,
        name: str | None = None,
        description: str | None = None,
        embedding: list[float] | None = None,
        content: str | None = None,
    ) -> RecallFile:
        from sqlmodel import select

        now = self._now()
        with self._sessions.session() as session:
            cat = session.scalar(
                select(self._sqla_models.RecallFile).where(self._sqla_models.RecallFile.id == category_id)
            )
            if cat is None:
                msg = f"Category with id {category_id} not found"
                raise KeyError(msg)

            if name is not None:
                cat.name = name
            if description is not None:
                cat.description = description
            if embedding is not None:
                cat.embedding = self._prepare_embedding(embedding)
            if content is not None:
                cat.content = content

            cat.updated_at = now
            session.add(cat)
            session.commit()
            session.refresh(cat)
            cat.embedding = self._normalize_embedding(cat.embedding)

        return self._cache_category(cat)

    def load_existing(self) -> None:
        from sqlmodel import select

        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.RecallFile)).all()
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                self._cache_category(row)

    def _cache_category(self, cat: RecallFile) -> RecallFile:
        self.categories[cat.id] = cat
        return cat


__all__ = ["PostgresRecallFileRepo"]
