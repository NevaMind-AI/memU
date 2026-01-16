"""SQLite memory category repository implementation."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from sqlmodel import delete, select

from memu.database.models import MemoryCategory
from memu.database.repositories.memory_category import MemoryCategoryRepo
from memu.database.sqlite.repositories.base import SQLiteRepoBase
from memu.database.sqlite.schema import SQLiteSQLAModels
from memu.database.sqlite.session import SQLiteSessionManager
from memu.database.state import DatabaseState

logger = logging.getLogger(__name__)


class SQLiteMemoryCategoryRepo(SQLiteRepoBase, MemoryCategoryRepo):
    """SQLite implementation of memory category repository."""

    def __init__(
        self,
        *,
        state: DatabaseState,
        memory_category_model: type[Any],
        sqla_models: SQLiteSQLAModels,
        sessions: SQLiteSessionManager,
        scope_fields: list[str],
    ) -> None:
        """Initialize memory category repository.

        Args:
            state: Shared database state for caching.
            memory_category_model: SQLModel class for memory categories.
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
        self._memory_category_model = memory_category_model
        self.categories = self._state.categories

    def list_categories(self, where: Mapping[str, Any] | None = None) -> dict[str, MemoryCategory]:
        """List categories matching the where clause.

        Args:
            where: Optional filter conditions.

        Returns:
            Dictionary of category ID to MemoryCategory mapping.
        """
        with self._sessions.session() as session:
            stmt = select(self._memory_category_model)
            filters = self._build_filters(self._memory_category_model, where)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.exec(stmt).all()

        result: dict[str, MemoryCategory] = {}
        for row in rows:
            cat = MemoryCategory(
                id=row.id,
                name=row.name,
                description=row.description,
                embedding=self._normalize_embedding(row.embedding_json),
                summary=row.summary,
                created_at=row.created_at,
                updated_at=row.updated_at,
                **self._scope_kwargs_from(row),
            )
            result[row.id] = cat
            self.categories[row.id] = cat

        return result

    def clear_categories(self, where: Mapping[str, Any] | None = None) -> dict[str, MemoryCategory]:
        """Clear categories matching the where clause.

        Args:
            where: Optional filter conditions.

        Returns:
            Dictionary of deleted category ID to MemoryCategory mapping.
        """
        filters = self._build_filters(self._memory_category_model, where)
        with self._sessions.session() as session:
            # First get the objects to delete
            stmt = select(self._memory_category_model)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.exec(stmt).all()

            deleted: dict[str, MemoryCategory] = {}
            for row in rows:
                cat = MemoryCategory(
                    id=row.id,
                    name=row.name,
                    description=row.description,
                    embedding=self._normalize_embedding(row.embedding_json),
                    summary=row.summary,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    **self._scope_kwargs_from(row),
                )
                deleted[row.id] = cat

            if not deleted:
                return {}

            # Delete from database
            del_stmt = delete(self._memory_category_model)
            if filters:
                del_stmt = del_stmt.where(*filters)
            session.exec(del_stmt)
            session.commit()

            # Clean up cache
            for cat_id in deleted:
                self.categories.pop(cat_id, None)

        return deleted

    def get_or_create_category(
        self, *, name: str, description: str, embedding: list[float], user_data: dict[str, Any]
    ) -> MemoryCategory:
        """Get existing category by name or create a new one.

        Args:
            name: Category name.
            description: Category description.
            embedding: Embedding vector.
            user_data: User scope data.

        Returns:
            Existing or newly created MemoryCategory.
        """
        # Check for existing category with same name and scope
        where: dict[str, Any] = {"name": name, **user_data}
        with self._sessions.session() as session:
            stmt = select(self._memory_category_model)
            filters = self._build_filters(self._memory_category_model, where)
            if filters:
                stmt = stmt.where(*filters)
            existing = session.exec(stmt).first()

            if existing:
                cat = MemoryCategory(
                    id=existing.id,
                    name=existing.name,
                    description=existing.description,
                    embedding=self._normalize_embedding(existing.embedding_json),
                    summary=existing.summary,
                    created_at=existing.created_at,
                    updated_at=existing.updated_at,
                    **self._scope_kwargs_from(existing),
                )
                self.categories[existing.id] = cat
                return cat

            # Create new category
            now = self._now()
            row = self._memory_category_model(
                name=name,
                description=description,
                embedding_json=self._prepare_embedding(embedding),
                summary=None,
                created_at=now,
                updated_at=now,
                **user_data,
            )
            session.add(row)
            session.commit()
            session.refresh(row)

        cat = MemoryCategory(
            id=row.id,
            name=row.name,
            description=row.description,
            embedding=embedding,
            summary=None,
            created_at=row.created_at,
            updated_at=row.updated_at,
            **user_data,
        )
        self.categories[row.id] = cat
        return cat

    def update_category(
        self,
        *,
        category_id: str,
        name: str | None = None,
        description: str | None = None,
        embedding: list[float] | None = None,
        summary: str | None = None,
    ) -> MemoryCategory:
        """Update an existing category.

        Args:
            category_id: ID of category to update.
            name: New name (optional).
            description: New description (optional).
            embedding: New embedding vector (optional).
            summary: New summary text (optional).

        Returns:
            Updated MemoryCategory object.

        Raises:
            KeyError: If category not found.
        """
        with self._sessions.session() as session:
            stmt = select(self._memory_category_model).where(self._memory_category_model.id == category_id)
            row = session.exec(stmt).first()

            if row is None:
                msg = f"Category with id {category_id} not found"
                raise KeyError(msg)

            if name is not None:
                row.name = name
            if description is not None:
                row.description = description
            if embedding is not None:
                row.embedding_json = self._prepare_embedding(embedding)
            if summary is not None:
                row.summary = summary
            row.updated_at = self._now()

            session.add(row)
            session.commit()
            session.refresh(row)

        cat = MemoryCategory(
            id=row.id,
            name=row.name,
            description=row.description,
            embedding=self._normalize_embedding(row.embedding_json),
            summary=row.summary,
            created_at=row.created_at,
            updated_at=row.updated_at,
            **self._scope_kwargs_from(row),
        )
        self.categories[row.id] = cat
        return cat

    def load_existing(self) -> None:
        """Load all existing categories from database into cache."""
        self.list_categories()


__all__ = ["SQLiteMemoryCategoryRepo"]
