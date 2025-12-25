from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from memu.database.models import MemoryCategory
from memu.database.postgres.repositories.base import PostgresRepoBase
from memu.database.postgres.session import SessionManager
from memu.database.repositories.memory_category import MemoryCategoryRepo
from memu.database.state import DatabaseState


class PostgresMemoryCategoryRepo(PostgresRepoBase, MemoryCategoryRepo):
    def __init__(
        self,
        *,
        state: DatabaseState,
        memory_category_model: type[MemoryCategory],
        sqla_models: Any,
        sessions: SessionManager,
        scope_fields: list[str],
    ) -> None:
        super().__init__(state=state, sqla_models=sqla_models, sessions=sessions, scope_fields=scope_fields)
        self._memory_category_model = memory_category_model
        self.categories: dict[str, MemoryCategory] = self._state.categories

    def list_categories(self, where: Mapping[str, Any] | None = None) -> dict[str, MemoryCategory]:
        from sqlmodel import select

        filters = self._build_filters(self._sqla_models.MemoryCategory, where)
        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.MemoryCategory).where(*filters)).all()
            result: dict[str, MemoryCategory] = {}
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                cat = self._cache_category(row)
                result[cat.id] = cat
        return result

    def get_or_create_category(
        self,
        *,
        name: str,
        description: str,
        embedding: list[float],
        user_data: dict[str, Any],
    ) -> MemoryCategory:
        from sqlmodel import select

        now = self._now()
        with self._sessions.session() as session:
            filters = [self._sqla_models.MemoryCategory.name == name]
            for key, value in user_data.items():
                filters.append(getattr(self._sqla_models.MemoryCategory, key) == value)
            existing = session.scalar(select(self._sqla_models.MemoryCategory).where(*filters))

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

            cat = self._memory_category_model(
                name=name,
                description=description,
                embedding=self._prepare_embedding(embedding),
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
        summary: str | None = None,
    ) -> MemoryCategory:
        from sqlmodel import select

        now = self._now()
        with self._sessions.session() as session:
            cat = session.scalar(
                select(self._sqla_models.MemoryCategory).where(self._sqla_models.MemoryCategory.id == category_id)
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
            if summary is not None:
                cat.summary = summary

            cat.updated_at = now
            session.add(cat)
            session.commit()
            session.refresh(cat)
            cat.embedding = self._normalize_embedding(cat.embedding)

        return self._cache_category(cat)

    def load_existing(self) -> None:
        from sqlmodel import select

        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.MemoryCategory)).all()
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                self._cache_category(row)

    def _cache_category(self, cat: MemoryCategory) -> MemoryCategory:
        self.categories[cat.id] = cat
        return cat


__all__ = ["PostgresMemoryCategoryRepo"]
