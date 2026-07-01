"""SQLite memory category repository implementation."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from sqlmodel import delete, select

from memu.database.models import RecallFile
from memu.database.repositories.recall_file import RecallFileRepo
from memu.database.sqlite.repositories.base import SQLiteRepoBase
from memu.database.sqlite.schema import SQLiteSQLAModels
from memu.database.sqlite.session import SQLiteSessionManager
from memu.database.state import DatabaseState

logger = logging.getLogger(__name__)


class SQLiteRecallFileRepo(SQLiteRepoBase, RecallFileRepo):
    """SQLite implementation of memory category repository."""

    def __init__(
        self,
        *,
        state: DatabaseState,
        recall_file_model: type[Any],
        sqla_models: SQLiteSQLAModels,
        sessions: SQLiteSessionManager,
        scope_fields: list[str],
    ) -> None:
        """Initialize memory category repository.

        Args:
            state: Shared database state for caching.
            recall_file_model: SQLModel class for memory categories.
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
        self._recall_file_model = recall_file_model
        self.categories = self._state.categories

    def list_categories(self, where: Mapping[str, Any] | None = None) -> dict[str, RecallFile]:
        """List categories matching the where clause.

        Args:
            where: Optional filter conditions.

        Returns:
            Dictionary of category ID to RecallFile mapping.
        """
        with self._sessions.session() as session:
            stmt = select(self._recall_file_model)
            filters = self._build_filters(self._recall_file_model, where)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.exec(stmt).all()

        result: dict[str, RecallFile] = {}
        for row in rows:
            cat = RecallFile(
                id=row.id,
                name=row.name,
                description=row.description,
                embedding=self._normalize_embedding(row.embedding),
                content=row.content,
                track=row.track,
                created_at=row.created_at,
                updated_at=row.updated_at,
                **self._scope_kwargs_from(row),
            )
            result[row.id] = cat
            self.categories[row.id] = cat

        return result

    def clear_categories(self, where: Mapping[str, Any] | None = None) -> dict[str, RecallFile]:
        """Clear categories matching the where clause.

        Args:
            where: Optional filter conditions.

        Returns:
            Dictionary of deleted category ID to RecallFile mapping.
        """
        filters = self._build_filters(self._recall_file_model, where)
        with self._sessions.session() as session:
            # First get the objects to delete
            stmt = select(self._recall_file_model)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.exec(stmt).all()

            deleted: dict[str, RecallFile] = {}
            for row in rows:
                cat = RecallFile(
                    id=row.id,
                    name=row.name,
                    description=row.description,
                    embedding=self._normalize_embedding(row.embedding),
                    content=row.content,
                    track=row.track,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    **self._scope_kwargs_from(row),
                )
                deleted[row.id] = cat

            if not deleted:
                return {}

            # Delete from database
            del_stmt = delete(self._recall_file_model)
            if filters:
                del_stmt = del_stmt.where(*filters)
            session.exec(del_stmt)
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
        """Get existing category by (name, track, scope) or create a new one.

        Args:
            name: Category name.
            description: Category description.
            embedding: Embedding vector.
            user_data: User scope data.
            track: Which track the file belongs to ("memory" or "skill").

        Returns:
            Existing or newly created RecallFile.
        """
        # Check for existing file with same name, track, and scope
        where: dict[str, Any] = {"name": name, "track": track, **user_data}
        with self._sessions.session() as session:
            stmt = select(self._recall_file_model)
            filters = self._build_filters(self._recall_file_model, where)
            if filters:
                stmt = stmt.where(*filters)
            existing = session.exec(stmt).first()

            if existing:
                cat = RecallFile(
                    id=existing.id,
                    name=existing.name,
                    description=existing.description,
                    embedding=self._normalize_embedding(existing.embedding),
                    content=existing.content,
                    track=existing.track,
                    created_at=existing.created_at,
                    updated_at=existing.updated_at,
                    **self._scope_kwargs_from(existing),
                )
                self.categories[existing.id] = cat
                return cat

            # Create new file
            now = self._now()
            row = self._recall_file_model(
                name=name,
                description=description,
                embedding=self._prepare_embedding(embedding),
                content=None,
                track=track,
                created_at=now,
                updated_at=now,
                **user_data,
            )
            session.add(row)
            session.commit()
            session.refresh(row)

        cat = RecallFile(
            id=row.id,
            name=row.name,
            description=row.description,
            embedding=embedding,
            content=None,
            track=track,
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
        content: str | None = None,
    ) -> RecallFile:
        """Update an existing category.

        Args:
            category_id: ID of category to update.
            name: New name (optional).
            description: New description (optional).
            embedding: New embedding vector (optional).
            content: New content text (optional).

        Returns:
            Updated RecallFile object.

        Raises:
            KeyError: If category not found.
        """
        with self._sessions.session() as session:
            stmt = select(self._recall_file_model).where(self._recall_file_model.id == category_id)
            row = session.exec(stmt).first()

            if row is None:
                msg = f"Category with id {category_id} not found"
                raise KeyError(msg)

            if name is not None:
                row.name = name
            if description is not None:
                row.description = description
            if embedding is not None:
                row.embedding = self._prepare_embedding(embedding)
            if content is not None:
                row.content = content
            row.updated_at = self._now()

            session.add(row)
            session.commit()
            session.refresh(row)

        cat = RecallFile(
            id=row.id,
            name=row.name,
            description=row.description,
            embedding=self._normalize_embedding(row.embedding),
            content=row.content,
            track=row.track,
            created_at=row.created_at,
            updated_at=row.updated_at,
            **self._scope_kwargs_from(row),
        )
        self.categories[row.id] = cat
        return cat

    def load_existing(self) -> None:
        """Load all existing categories from database into cache."""
        self.list_categories()


__all__ = ["SQLiteRecallFileRepo"]
