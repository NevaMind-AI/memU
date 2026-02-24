"""SQLite memory item repository implementation."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import pendulum
from sqlmodel import delete, select

from memu.database.inmemory.vector import cosine_topk, cosine_topk_salience
from memu.database.models import MemoryItem, MemoryType, compute_content_hash
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

    def list_items_by_ref_ids(
        self, ref_ids: list[str], where: Mapping[str, Any] | None = None
    ) -> dict[str, MemoryItem]:
        """List items by their ref_id in the extra column.

        Args:
            ref_ids: List of ref_ids to query.
            where: Additional filter conditions.

        Returns:
            Dict mapping item_id -> MemoryItem for items whose extra.ref_id is in ref_ids.
        """
        if not ref_ids:
            return {}

        from sqlalchemy import func

        with self._sessions.session() as session:
            stmt = select(self._memory_item_model)
            filters = self._build_filters(self._memory_item_model, where)
            # Add filter for json_extract(extra, '$.ref_id') IN ref_ids (only rows with ref_id key)
            ref_id_col = func.json_extract(self._memory_item_model.extra, "$.ref_id")
            filters.append(ref_id_col.isnot(None))
            filters.append(ref_id_col.in_(ref_ids))
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
        reinforce: bool = False,
        tool_record: dict[str, Any] | None = None,
    ) -> MemoryItem:
        """Create a new memory item.

        Args:
            resource_id: Associated resource ID.
            memory_type: Type of memory.
            summary: Memory summary text.
            embedding: Embedding vector.
            user_data: User scope data.
            reinforce: If True, reinforce existing item instead of creating duplicate.
            tool_record: Tool-related fields (when_to_use, metadata, tool_calls) to store in extra.

        Returns:
            Created MemoryItem object.
        """
        if reinforce and memory_type != "tool":
            return self.create_item_reinforce(
                resource_id=resource_id,
                memory_type=memory_type,
                summary=summary,
                embedding=embedding,
                user_data=user_data,
            )

        # Build extra dict with tool_record fields at top level
        extra: dict[str, Any] = {}
        if tool_record:
            if tool_record.get("when_to_use") is not None:
                extra["when_to_use"] = tool_record["when_to_use"]
            if tool_record.get("metadata") is not None:
                extra["metadata"] = tool_record["metadata"]
            if tool_record.get("tool_calls") is not None:
                extra["tool_calls"] = tool_record["tool_calls"]

        now = self._now()
        row = self._memory_item_model(
            resource_id=resource_id,
            memory_type=memory_type,
            summary=summary,
            embedding_json=self._prepare_embedding(embedding),
            extra=extra if extra else {},
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
            extra=row.extra,
            created_at=row.created_at,
            updated_at=row.updated_at,
            **user_data,
        )
        self.items[row.id] = item
        return item

    def create_item_reinforce(
        self,
        *,
        resource_id: str,
        memory_type: MemoryType,
        summary: str,
        embedding: list[float],
        user_data: dict[str, Any],
    ) -> MemoryItem:
        """Create or reinforce a memory item with deduplication.

        If an item with the same content hash exists in the same scope,
        reinforce it instead of creating a duplicate.

        Args:
            resource_id: Associated resource ID.
            memory_type: Type of memory.
            summary: Memory summary text.
            embedding: Embedding vector.
            user_data: User scope data.

        Returns:
            Created or reinforced MemoryItem object.
        """
        from sqlalchemy import func

        content_hash = compute_content_hash(summary, memory_type)

        with self._sessions.session() as session:
            # Check for existing item with same hash in same scope (deduplication)
            # Use json_extract(extra, '$.content_hash') for query
            content_hash_col = func.json_extract(self._memory_item_model.extra, "$.content_hash")
            filters = [content_hash_col == content_hash]
            filters.extend(self._build_filters(self._memory_item_model, user_data))

            existing = session.exec(select(self._memory_item_model).where(*filters)).first()

            if existing:
                # Reinforce existing memory instead of creating duplicate
                current_extra = existing.extra or {}
                current_count = current_extra.get("reinforcement_count", 1)
                existing.extra = {
                    **current_extra,
                    "reinforcement_count": current_count + 1,
                    "last_reinforced_at": self._now().isoformat(),
                }
                existing.updated_at = self._now()
                session.add(existing)
                session.commit()
                session.refresh(existing)

                item = MemoryItem(
                    id=existing.id,
                    resource_id=existing.resource_id,
                    memory_type=existing.memory_type,
                    summary=existing.summary,
                    embedding=self._normalize_embedding(existing.embedding_json),
                    created_at=existing.created_at,
                    updated_at=existing.updated_at,
                    extra=existing.extra,
                    **self._scope_kwargs_from(existing),
                )
                self.items[existing.id] = item
                return item

            # Create new item with salience tracking in extra
            now = self._now()
            item_extra = user_data.pop("extra", {}) if "extra" in user_data else {}
            item_extra.update({
                "content_hash": content_hash,
                "reinforcement_count": 1,
                "last_reinforced_at": now.isoformat(),
            })

            row = self._memory_item_model(
                resource_id=resource_id,
                memory_type=memory_type,
                summary=summary,
                embedding_json=self._prepare_embedding(embedding),
                extra=item_extra,
                created_at=now,
                updated_at=now,
                **user_data,
            )

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
            extra=row.extra,
            **self._scope_kwargs_from(row),
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
        extra: dict[str, Any] | None = None,
        tool_record: dict[str, Any] | None = None,
    ) -> MemoryItem:
        """Update an existing memory item.

        Args:
            item_id: ID of item to update.
            memory_type: New memory type (optional).
            summary: New summary text (optional).
            embedding: New embedding vector (optional).
            extra: Extra data to merge into existing extra dict (optional).
            tool_record: Tool-related fields (when_to_use, metadata, tool_calls) to merge into extra.

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

            # Merge extra and tool_record into existing extra dict
            current_extra = row.extra or {}
            if extra is not None:
                current_extra = {**current_extra, **extra}
            if tool_record is not None:
                # Merge tool_record fields at top level
                for key in ("when_to_use", "metadata", "tool_calls"):
                    if tool_record.get(key) is not None:
                        current_extra[key] = tool_record[key]
            if extra is not None or tool_record is not None:
                row.extra = current_extra

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
            extra=row.extra,
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
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
        *,
        ranking: str = "similarity",
        recency_decay_days: float = 30.0,
    ) -> list[tuple[str, float]]:
        """Perform vector similarity search on memory items.

        Uses brute-force cosine similarity since SQLite doesn't have native vector support.

        Args:
            query_vec: Query embedding vector.
            top_k: Maximum number of results to return.
            where: Optional filter conditions.
            ranking: Ranking strategy - "similarity" (default) or "salience".
            recency_decay_days: Half-life for recency decay in salience ranking.

        Returns:
            List of (item_id, similarity_score) tuples.
        """
        # Load items from database with filters
        pool = self.list_items(where)

        if ranking == "salience":
            # Salience-aware ranking: similarity x reinforcement x recency
            # Read values from extra dict
            corpus = [
                (
                    i.id,
                    i.embedding,
                    (i.extra or {}).get("reinforcement_count", 1),
                    self._parse_datetime((i.extra or {}).get("last_reinforced_at")),
                )
                for i in pool.values()
            ]
            return cosine_topk_salience(query_vec, corpus, k=top_k, recency_decay_days=recency_decay_days)

        # Default: pure cosine similarity (backward compatible)
        hits = cosine_topk(query_vec, [(i.id, i.embedding) for i in pool.values()], k=top_k)
        return hits

    @staticmethod
    def _parse_datetime(dt_str: str | None) -> pendulum.DateTime | None:
        """Parse ISO datetime string from extra dict."""
        if dt_str is None:
            return None
        try:
            parsed = pendulum.parse(dt_str)
        except (ValueError, TypeError):
            return None
        else:
            if isinstance(parsed, pendulum.DateTime):
                return parsed
            return None

    def load_existing(self) -> None:
        """Load all existing items from database into cache."""
        self.list_items()


__all__ = ["SQLiteMemoryItemRepo"]
