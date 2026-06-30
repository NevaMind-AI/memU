"""SQLite category-item relation repository implementation."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from sqlmodel import select

from memu.database.models import RecallFileEntry
from memu.database.repositories.recall_file_entry import RecallFileEntryRepo
from memu.database.sqlite.repositories.base import SQLiteRepoBase
from memu.database.sqlite.schema import SQLiteSQLAModels
from memu.database.sqlite.session import SQLiteSessionManager
from memu.database.state import DatabaseState

logger = logging.getLogger(__name__)


class SQLiteRecallFileEntryRepo(SQLiteRepoBase, RecallFileEntryRepo):
    """SQLite implementation of category-item relation repository."""

    def __init__(
        self,
        *,
        state: DatabaseState,
        recall_file_entry_model: type[Any],
        sqla_models: SQLiteSQLAModels,
        sessions: SQLiteSessionManager,
        scope_fields: list[str],
    ) -> None:
        """Initialize category-item repository.

        Args:
            state: Shared database state for caching.
            recall_file_entry_model: SQLModel class for category-item relations.
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
        self._recall_file_entry_model = recall_file_entry_model
        self.relations = self._state.relations

    def list_relations(self, where: Mapping[str, Any] | None = None) -> list[RecallFileEntry]:
        """List category-item relations matching the where clause.

        Args:
            where: Optional filter conditions.

        Returns:
            List of RecallFileEntry relations.
        """
        with self._sessions.session() as session:
            stmt = select(self._recall_file_entry_model)
            filters = self._build_filters(self._recall_file_entry_model, where)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.exec(stmt).all()

        result: list[RecallFileEntry] = []
        for row in rows:
            rel = RecallFileEntry(
                id=row.id,
                item_id=row.item_id,
                category_id=row.category_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
                **self._scope_kwargs_from(row),
            )
            result.append(rel)
            # Update cache
            if not any(r.id == rel.id for r in self.relations):
                self.relations.append(rel)

        return result

    def link_item_category(self, item_id: str, category_id: str, user_data: dict[str, Any]) -> RecallFileEntry:
        """Create a link between an item and a category.

        Args:
            item_id: Memory item ID.
            category_id: Category ID.
            user_data: User scope data.

        Returns:
            Created RecallFileEntry relation.
        """
        # Check if relation already exists
        where: dict[str, Any] = {
            "item_id": item_id,
            "category_id": category_id,
            **user_data,
        }
        with self._sessions.session() as session:
            stmt = select(self._recall_file_entry_model)
            filters = self._build_filters(self._recall_file_entry_model, where)
            if filters:
                stmt = stmt.where(*filters)
            existing = session.exec(stmt).first()

            if existing:
                rel = RecallFileEntry(
                    id=existing.id,
                    item_id=existing.item_id,
                    category_id=existing.category_id,
                    created_at=existing.created_at,
                    updated_at=existing.updated_at,
                    **self._scope_kwargs_from(existing),
                )
                return rel

            # Create new relation
            now = self._now()
            row = self._recall_file_entry_model(
                item_id=item_id,
                category_id=category_id,
                created_at=now,
                updated_at=now,
                **user_data,
            )
            session.add(row)
            session.commit()
            session.refresh(row)

        rel = RecallFileEntry(
            id=row.id,
            item_id=row.item_id,
            category_id=row.category_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            **user_data,
        )
        self.relations.append(rel)
        return rel

    def unlink_item_category(self, item_id: str, category_id: str) -> None:
        """Remove a link between an item and a category.

        Args:
            item_id: Memory item ID.
            category_id: Category ID.
        """
        with self._sessions.session() as session:
            stmt = select(self._recall_file_entry_model).where(
                self._recall_file_entry_model.item_id == item_id,
                self._recall_file_entry_model.category_id == category_id,
            )
            row = session.exec(stmt).first()
            if row:
                session.delete(row)
                session.commit()
                # Remove from cache
                self.relations[:] = [
                    r for r in self.relations if not (r.item_id == item_id and r.category_id == category_id)
                ]

    def unlink_item(self, item_id: str) -> list[RecallFileEntry]:
        """Remove all relations for a given item (used on item deletion)."""
        from sqlmodel import delete

        removed = self.list_relations({"item_id": item_id})
        if not removed:
            return []
        with self._sessions.session() as session:
            session.exec(delete(self._recall_file_entry_model).where(self._recall_file_entry_model.item_id == item_id))
            session.commit()
        self.relations[:] = [r for r in self.relations if r.item_id != item_id]
        return removed

    def clear_relations(self, where: Mapping[str, Any] | None = None) -> list[RecallFileEntry]:
        """Remove all relations matching the scope (used on clear_memory)."""
        from sqlmodel import delete

        removed = self.list_relations(where)
        if not removed:
            return []
        filters = self._build_filters(self._recall_file_entry_model, where)
        with self._sessions.session() as session:
            del_stmt = delete(self._recall_file_entry_model)
            if filters:
                del_stmt = del_stmt.where(*filters)
            session.exec(del_stmt)
            session.commit()
        removed_ids = {rel.id for rel in removed}
        self.relations[:] = [r for r in self.relations if r.id not in removed_ids]
        return removed

    def get_item_categories(self, item_id: str) -> list[RecallFileEntry]:
        """Get all category relations for a given item.

        Args:
            item_id: Memory item ID.

        Returns:
            List of RecallFileEntry relations for the item.
        """
        return self.list_relations({"item_id": item_id})

    def load_existing(self) -> None:
        """Load all existing relations from database into cache."""
        self.list_relations()


__all__ = ["SQLiteRecallFileEntryRepo"]
