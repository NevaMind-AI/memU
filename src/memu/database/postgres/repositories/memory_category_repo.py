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
        if not where:
            return dict(self.categories)

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

    def get_or_create_category(self, *, name: str, description: str, embedding: list[float]) -> MemoryCategory:
        from sqlmodel import select

        now = self._now()
        with self._sessions.session() as session:
            existing = session.scalar(
                select(self._sqla_models.MemoryCategory).where(self._sqla_models.MemoryCategory.name == name)
            )

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
            )
            session.add(cat)
            session.commit()
            session.refresh(cat)

        return self._cache_category(cat)

    def load_existing(self) -> None:
        from sqlmodel import select

        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.MemoryCategory)).all()
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                self._cache_category(row)

    def _cache_category(self, cat: MemoryCategory) -> MemoryCategory:
        existing = self.categories.get(cat.id)
        if existing:
            return existing
        self.categories[cat.id] = cat
        return cat


__all__ = ["PostgresMemoryCategoryRepo"]
