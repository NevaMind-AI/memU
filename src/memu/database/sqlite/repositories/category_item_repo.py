"""SQLite category-item relation repository implementation."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from sqlmodel import delete, select

from memu.database.models import CategoryItem
from memu.database.repositories.category_item import CategoryItemRepo
from memu.database.sqlite.repositories.base import SQLiteRepoBase
from memu.database.sqlite.schema import SQLiteSQLAModels
from memu.database.sqlite.session import SQLiteSessionManager
from memu.database.state import DatabaseState

logger = logging.getLogger(__name__)


class SQLiteCategoryItemRepo(SQLiteRepoBase, CategoryItemRepo):
    """SQLite implementation of category-item relation repository."""

    def __init__(
        self,
        *,
        state: DatabaseState,
        category_item_model: type[Any],
        sqla_models: SQLiteSQLAModels,
        sessions: SQLiteSessionManager,
        scope_fields: list[str],
    ) -> None:
        """Initialize category-item repository.

        Args:
            state: Shared database state for caching.
            category_item_model: SQLModel class for category-item relations.
            sqla_models: SQLAlchemy model container.
            sessions: Session manager for database connections.
            scope_fields: List of user scope field names.
        """
        super().__init__(
            state=state,
            sqla_models=sqla_models,
            sessions=sessions,
            scope_fields=scope_fields,
        )
        self._category_item_model = category_item_model
        self.relations = self._state.relations

    def list_relations(self, where: Mapping[str, Any] | None = None) -> list[CategoryItem]:
        """List category-item relations matching the where clause.

        Args:
            where: Optional filter conditions.

        Returns:
            List of CategoryItem relations.
        """
        with self._sessions.session() as session:
            stmt = select(self._category_item_model)
            filters = self._build_filters(self._category_item_model, where)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.exec(stmt).all()

        result: list[CategoryItem] = []
        for row in rows:
            rel = self._relation_from_row(row)
            result.append(rel)
            self._cache_relation(rel)

        return result

    def clear_relations(self, where: Mapping[str, Any] | None = None) -> list[CategoryItem]:
        """Clear category-item relations matching the where clause."""
        filters = self._build_filters(self._category_item_model, where)
        with self._sessions.session() as session:
            stmt = select(self._category_item_model)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.exec(stmt).all()
            deleted = [self._relation_from_row(row) for row in rows]

            if not deleted:
                return []

            del_stmt = delete(self._category_item_model)
            if filters:
                del_stmt = del_stmt.where(*filters)
            session.exec(del_stmt)
            session.commit()

        deleted_ids = {rel.id for rel in deleted}
        self.relations[:] = [rel for rel in self.relations if rel.id not in deleted_ids]
        return deleted

    def link_item_category(self, item_id: str, category_id: str, user_data: dict[str, Any]) -> CategoryItem:
        """Create a link between an item and a category.

        Args:
            item_id: Memory item ID.
            category_id: Category ID.
            user_data: User scope data.

        Returns:
            Created CategoryItem relation.
        """
        # Check if relation already exists
        where: dict[str, Any] = {
            "item_id": item_id,
            "category_id": category_id,
            **user_data,
        }
        with self._sessions.session() as session:
            stmt = select(self._category_item_model)
            filters = self._build_filters(self._category_item_model, where)
            if filters:
                stmt = stmt.where(*filters)
            existing = session.exec(stmt).first()

            if existing:
                return self._cache_relation(self._relation_from_row(existing))

            # Create new relation
            now = self._now()
            row = self._category_item_model(
                item_id=item_id,
                category_id=category_id,
                created_at=now,
                updated_at=now,
                **user_data,
            )
            session.add(row)
            session.commit()
            session.refresh(row)

        return self._cache_relation(self._relation_from_row(row))

    def unlink_item_category(self, item_id: str, category_id: str) -> None:
        """Remove a link between an item and a category.

        Args:
            item_id: Memory item ID.
            category_id: Category ID.
        """
        with self._sessions.session() as session:
            stmt = select(self._category_item_model).where(
                self._category_item_model.item_id == item_id,
                self._category_item_model.category_id == category_id,
            )
            row = session.exec(stmt).first()
            if row:
                session.delete(row)
                session.commit()
                # Remove from cache
                self.relations[:] = [
                    r for r in self.relations if not (r.item_id == item_id and r.category_id == category_id)
                ]

    def get_item_categories(self, item_id: str) -> list[CategoryItem]:
        """Get all category relations for a given item.

        Args:
            item_id: Memory item ID.

        Returns:
            List of CategoryItem relations for the item.
        """
        return self.list_relations({"item_id": item_id})

    def load_existing(self) -> None:
        """Load all existing relations from database into cache."""
        self.list_relations()

    def _relation_from_row(self, row: Any) -> CategoryItem:
        return CategoryItem(
            id=row.id,
            item_id=row.item_id,
            category_id=row.category_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            **self._scope_kwargs_from(row),
        )

    def _cache_relation(self, rel: CategoryItem) -> CategoryItem:
        for idx, existing in enumerate(self.relations):
            if existing.id == rel.id:
                self.relations[idx] = rel
                return rel
        self.relations.append(rel)
        return rel


__all__ = ["SQLiteCategoryItemRepo"]
