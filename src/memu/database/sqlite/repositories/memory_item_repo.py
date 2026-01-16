"""SQLite memory item repository implementation."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from sqlmodel import delete, select

from memu.database.inmemory.vector import cosine_topk
from memu.database.models import MemoryItem, MemoryType
from memu.database.repositories.memory_item import MemoryItemRepo
from memu.database.sqlite.repositories.base import SQLiteRepoBase
from memu.database.sqlite.schema import SQLiteSQLAModels
from memu.database.sqlite.session import SQLiteSessionManager
from memu.database.state import DatabaseState

logger = logging.getLogger(__name__)


class SQLiteMemoryItemRepo(SQLiteRepoBase, MemoryItemRepo):
    """SQLite implementation of memory item repository."""

    def __init__(
        self,
        *,
        state: DatabaseState,
        memory_item_model: type[Any],
        sqla_models: SQLiteSQLAModels,
        sessions: SQLiteSessionManager,
        scope_fields: list[str],
    ) -> None:
        """Initialize memory item repository.

        Args:
            state: Shared database state for caching.
            memory_item_model: SQLModel class for memory items.
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
        self._memory_item_model = memory_item_model
        self.items = self._state.items

    def get_item(self, item_id: str) -> MemoryItem | None:
        """Get a memory item by ID.

        Args:
            item_id: The item ID to look up.

        Returns:
            MemoryItem if found, None otherwise.
        """
        # Check cache first
        if item_id in self.items:
            return self.items[item_id]

        with self._sessions.session() as session:
            stmt = select(self._memory_item_model).where(self._memory_item_model.id == item_id)
            row = session.exec(stmt).first()

        if row is None:
            return None

        item = MemoryItem(
            id=row.id,
            resource_id=row.resource_id,
            memory_type=row.memory_type,
            summary=row.summary,
            embedding=self._normalize_embedding(row.embedding_json),
            created_at=row.created_at,
            updated_at=row.updated_at,
            **self._scope_kwargs_from(row),
        )
        self.items[row.id] = item
        return item

    def list_items(self, where: Mapping[str, Any] | None = None) -> dict[str, MemoryItem]:
        """List memory items matching the where clause.

        Args:
            where: Optional filter conditions.

        Returns:
            Dictionary of item ID to MemoryItem mapping.
        """
        with self._sessions.session() as session:
            stmt = select(self._memory_item_model)
            filters = self._build_filters(self._memory_item_model, where)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.exec(stmt).all()

        result: dict[str, MemoryItem] = {}
        for row in rows:
            item = MemoryItem(
                id=row.id,
                resource_id=row.resource_id,
                memory_type=row.memory_type,
                summary=row.summary,
                embedding=self._normalize_embedding(row.embedding_json),
                created_at=row.created_at,
                updated_at=row.updated_at,
                **self._scope_kwargs_from(row),
            )
            result[row.id] = item
            self.items[row.id] = item

        return result

    def clear_items(self, where: Mapping[str, Any] | None = None) -> dict[str, MemoryItem]:
        """Clear items matching the where clause.

        Args:
            where: Optional filter conditions.

        Returns:
            Dictionary of deleted item ID to MemoryItem mapping.
        """
        filters = self._build_filters(self._memory_item_model, where)
        with self._sessions.session() as session:
            # First get the objects to delete
            stmt = select(self._memory_item_model)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.exec(stmt).all()

            deleted: dict[str, MemoryItem] = {}
            for row in rows:
                item = MemoryItem(
                    id=row.id,
                    resource_id=row.resource_id,
                    memory_type=row.memory_type,
                    summary=row.summary,
                    embedding=self._normalize_embedding(row.embedding_json),
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    **self._scope_kwargs_from(row),
                )
                deleted[row.id] = item

            if not deleted:
                return {}

            # Delete from database
            del_stmt = delete(self._memory_item_model)
            if filters:
                del_stmt = del_stmt.where(*filters)
            session.exec(del_stmt)
            session.commit()

            # Clean up cache
            for item_id in deleted:
                self.items.pop(item_id, None)

        return deleted

    def create_item(
        self,
        *,
        resource_id: str,
        memory_type: MemoryType,
        summary: str,
        embedding: list[float],
        user_data: dict[str, Any],
    ) -> MemoryItem:
        """Create a new memory item.

        Args:
            resource_id: Associated resource ID.
            memory_type: Type of memory.
            summary: Memory summary text.
            embedding: Embedding vector.
            user_data: User scope data.

        Returns:
            Created MemoryItem object.
        """
        now = self._now()
        row = self._memory_item_model(
            resource_id=resource_id,
            memory_type=memory_type,
            summary=summary,
            embedding_json=self._prepare_embedding(embedding),
            created_at=now,
            updated_at=now,
            **user_data,
        )
        with self._sessions.session() as session:
            session.add(row)
            session.commit()
            session.refresh(row)

        item = MemoryItem(
            id=row.id,
            resource_id=row.resource_id,
            memory_type=row.memory_type,
            summary=row.summary,
            embedding=embedding,
            created_at=row.created_at,
            updated_at=row.updated_at,
            **user_data,
        )
        self.items[row.id] = item
        return item

    def update_item(
        self,
        *,
        item_id: str,
        memory_type: MemoryType | None = None,
        summary: str | None = None,
        embedding: list[float] | None = None,
    ) -> MemoryItem:
        """Update an existing memory item.

        Args:
            item_id: ID of item to update.
            memory_type: New memory type (optional).
            summary: New summary text (optional).
            embedding: New embedding vector (optional).

        Returns:
            Updated MemoryItem object.

        Raises:
            KeyError: If item not found.
        """
        with self._sessions.session() as session:
            stmt = select(self._memory_item_model).where(self._memory_item_model.id == item_id)
            row = session.exec(stmt).first()

            if row is None:
                msg = f"Item with id {item_id} not found"
                raise KeyError(msg)

            if memory_type is not None:
                row.memory_type = memory_type
            if summary is not None:
                row.summary = summary
            if embedding is not None:
                row.embedding_json = self._prepare_embedding(embedding)
            row.updated_at = self._now()

            session.add(row)
            session.commit()
            session.refresh(row)

        item = MemoryItem(
            id=row.id,
            resource_id=row.resource_id,
            memory_type=row.memory_type,
            summary=row.summary,
            embedding=self._normalize_embedding(row.embedding_json),
            created_at=row.created_at,
            updated_at=row.updated_at,
            **self._scope_kwargs_from(row),
        )
        self.items[row.id] = item
        return item

    def delete_item(self, item_id: str) -> None:
        """Delete a memory item.

        Args:
            item_id: ID of item to delete.
        """
        with self._sessions.session() as session:
            stmt = select(self._memory_item_model).where(self._memory_item_model.id == item_id)
            row = session.exec(stmt).first()
            if row:
                session.delete(row)
                session.commit()

        if item_id in self.items:
            del self.items[item_id]

    def vector_search_items(
        self, query_vec: list[float], top_k: int, where: Mapping[str, Any] | None = None
    ) -> list[tuple[str, float]]:
        """Perform vector similarity search on memory items.

        Uses brute-force cosine similarity since SQLite doesn't have native vector support.

        Args:
            query_vec: Query embedding vector.
            top_k: Maximum number of results to return.
            where: Optional filter conditions.

        Returns:
            List of (item_id, similarity_score) tuples.
        """
        # Load items from database with filters
        pool = self.list_items(where)
        # Use brute-force cosine similarity
        hits = cosine_topk(query_vec, [(i.id, i.embedding) for i in pool.values()], k=top_k)
        return hits

    def load_existing(self) -> None:
        """Load all existing items from database into cache."""
        self.list_items()


__all__ = ["SQLiteMemoryItemRepo"]
