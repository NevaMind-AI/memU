from __future__ import annotations

from typing import Any

from memu.database.models import CategoryItem
from memu.database.postgres.repositories.base import PostgresRepoBase
from memu.database.postgres.session import SessionManager
from memu.database.repositories.category_item import CategoryItemRepo
from memu.database.state import DatabaseState


class PostgresCategoryItemRepo(PostgresRepoBase, CategoryItemRepo):
    def __init__(
        self,
        *,
        state: DatabaseState,
        category_item_model: type[CategoryItem],
        sqla_models: Any,
        sessions: SessionManager,
        scope_fields: list[str],
    ) -> None:
        super().__init__(state=state, sqla_models=sqla_models, sessions=sessions, scope_fields=scope_fields)
        self._category_item_model = category_item_model
        self.relations: list[CategoryItem] = self._state.relations

    def link_item_category(self, item_id: str, cat_id: str) -> CategoryItem:
        from sqlmodel import select

        # Avoid duplicate inserts using local cache
        for rel in self.relations:
            if rel.item_id == item_id and rel.category_id == cat_id:
                return rel

        now = self._now()
        new_rel = self._category_item_model(
            item_id=item_id,
            category_id=cat_id,
            created_at=now,
            updated_at=now,
        )

        with self._sessions.session() as session:
            existing = session.scalar(
                select(self._sqla_models.CategoryItem).where(
                    self._sqla_models.CategoryItem.item_id == item_id,
                    self._sqla_models.CategoryItem.category_id == cat_id,
                )
            )
            if existing:
                return self._cache_relation(existing)

            session.add(new_rel)
            session.commit()
            session.refresh(new_rel)

        return self._cache_relation(new_rel)

    def load_existing(self) -> None:
        from sqlmodel import select

        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.CategoryItem)).all()
            for row in rows:
                self._cache_relation(row)

    def _cache_relation(self, rel: CategoryItem) -> CategoryItem:
        for existing in self.relations:
            if existing.id == getattr(rel, "id", None):
                return existing
        self.relations.append(rel)
        return rel


__all__ = ["PostgresCategoryItemRepo"]
