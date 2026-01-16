from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from memu.database.models import CategoryItem
from memu.database.postgres.repositories.base import PostgresRepoBase
from memu.database.postgres.session import AsyncSessionManager, SessionManager
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
        async_sessions: AsyncSessionManager | None = None,
        scope_fields: list[str],
    ) -> None:
        super().__init__(
            state=state,
            sqla_models=sqla_models,
            sessions=sessions,
            async_sessions=async_sessions,
            scope_fields=scope_fields,
        )
        self._category_item_model = category_item_model
        self.relations: list[CategoryItem] = self._state.relations

    def list_relations(self, where: Mapping[str, Any] | None = None) -> list[CategoryItem]:
        from sqlmodel import select

        filters = self._build_filters(self._sqla_models.CategoryItem, where)
        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.CategoryItem).where(*filters)).all()
        return [self._cache_relation(row) for row in rows]

    def link_item_category(self, item_id: str, cat_id: str, user_data: dict[str, Any]) -> CategoryItem:
        from sqlmodel import select

        # Avoid duplicate inserts using local cache
        for rel in self.relations:
            if rel.item_id == item_id and rel.category_id == cat_id:
                return rel

        now = self._now()
        new_rel = self._category_item_model(
            item_id=item_id,
            category_id=cat_id,
            **user_data,
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

    def unlink_item_category(self, item_id: str, cat_id: str) -> None:
        from sqlmodel import delete

        with self._sessions.session() as session:
            session.exec(
                delete(self._sqla_models.CategoryItem).where(
                    self._sqla_models.CategoryItem.item_id == item_id,
                    self._sqla_models.CategoryItem.category_id == cat_id,
                )
            )
            session.commit()

    def get_item_categories(self, item_id: str) -> list[CategoryItem]:
        from sqlmodel import select

        with self._sessions.session() as session:
            rows = session.scalars(
                select(self._sqla_models.CategoryItem).where(self._sqla_models.CategoryItem.item_id == item_id)
            ).all()
        return [self._cache_relation(row) for row in rows]

    def load_existing(self) -> None:
        from sqlmodel import select

        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.CategoryItem)).all()
            for row in rows:
                self._cache_relation(row)

    def _cache_relation(self, rel: CategoryItem) -> CategoryItem:
        self.relations.append(rel)
        return rel

    async def list_relations_async(self, where: Mapping[str, Any] | None = None) -> list[CategoryItem]:
        if self._async_sessions is None:
            raise RuntimeError("Async sessions not initialized")
        from sqlalchemy import select

        filters = self._build_filters(self._sqla_models.CategoryItem, where)
        async with self._async_sessions.session() as session:
            result = await session.execute(select(self._sqla_models.CategoryItem).where(*filters))
            rows = result.scalars().all()
        return [self._cache_relation(row) for row in rows]

    async def link_item_category_async(self, item_id: str, cat_id: str, user_data: dict[str, Any]) -> CategoryItem:
        if self._async_sessions is None:
            raise RuntimeError("Async sessions not initialized")
        from sqlalchemy import select

        for rel in self.relations:
            if rel.item_id == item_id and rel.category_id == cat_id:
                return rel

        now = self._now()
        new_rel = self._category_item_model(
            item_id=item_id,
            category_id=cat_id,
            **user_data,
            created_at=now,
            updated_at=now,
        )

        async with self._async_sessions.session() as session:
            result = await session.execute(
                select(self._sqla_models.CategoryItem).where(
                    self._sqla_models.CategoryItem.item_id == item_id,
                    self._sqla_models.CategoryItem.category_id == cat_id,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return self._cache_relation(existing)

            session.add(new_rel)
            await session.commit()
            await session.refresh(new_rel)

        return self._cache_relation(new_rel)

    async def unlink_item_category_async(self, item_id: str, cat_id: str) -> None:
        if self._async_sessions is None:
            raise RuntimeError("Async sessions not initialized")
        from sqlalchemy import delete

        async with self._async_sessions.session() as session:
            await session.execute(
                delete(self._sqla_models.CategoryItem).where(
                    self._sqla_models.CategoryItem.item_id == item_id,
                    self._sqla_models.CategoryItem.category_id == cat_id,
                )
            )
            await session.commit()

    async def get_item_categories_async(self, item_id: str) -> list[CategoryItem]:
        if self._async_sessions is None:
            raise RuntimeError("Async sessions not initialized")
        from sqlalchemy import select

        async with self._async_sessions.session() as session:
            result = await session.execute(
                select(self._sqla_models.CategoryItem).where(self._sqla_models.CategoryItem.item_id == item_id)
            )
            rows = result.scalars().all()
        return [self._cache_relation(row) for row in rows]

    async def load_existing_async(self) -> None:
        if self._async_sessions is None:
            raise RuntimeError("Async sessions not initialized")
        from sqlalchemy import select

        async with self._async_sessions.session() as session:
            result = await session.execute(select(self._sqla_models.CategoryItem))
            rows = result.scalars().all()
            for row in rows:
                self._cache_relation(row)


__all__ = ["PostgresCategoryItemRepo"]
