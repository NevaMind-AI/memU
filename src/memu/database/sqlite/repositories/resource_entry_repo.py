"""SQLite entry <-> resource membership-edge repository implementation."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from sqlmodel import delete, select

from memu.database.models import ResourceEntry
from memu.database.repositories.resource_entry import ResourceEntryRepo
from memu.database.sqlite.repositories.base import SQLiteRepoBase
from memu.database.sqlite.schema import SQLiteSQLAModels
from memu.database.sqlite.session import SQLiteSessionManager
from memu.database.state import DatabaseState

logger = logging.getLogger(__name__)


class SQLiteResourceEntryRepo(SQLiteRepoBase, ResourceEntryRepo):
    """SQLite implementation of the entry <-> coarse-resource edge repository."""

    def __init__(
        self,
        *,
        state: DatabaseState,
        resource_entry_model: type[Any],
        sqla_models: SQLiteSQLAModels,
        sessions: SQLiteSessionManager,
        scope_fields: list[str],
    ) -> None:
        """Initialize resource-entry repository.

        Args:
            state: Shared database state for caching.
            resource_entry_model: SQLModel class for membership edges.
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
        self._resource_entry_model = resource_entry_model
        self.relations = self._state.relations

    def _row_to_relation(self, row: Any) -> ResourceEntry:
        """Map an ORM row to a backend-agnostic ResourceEntry record."""
        return ResourceEntry(
            id=row.id,
            entry_id=row.entry_id,
            resource_id=row.resource_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            **self._scope_kwargs_from(row),
        )

    def list_relations(self, where: Mapping[str, Any] | None = None) -> list[ResourceEntry]:
        """List membership edges matching the where clause."""
        with self._sessions.session() as session:
            stmt = select(self._resource_entry_model)
            filters = self._build_filters(self._resource_entry_model, where)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.exec(stmt).all()

        result: list[ResourceEntry] = []
        for row in rows:
            rel = self._row_to_relation(row)
            result.append(rel)
            if not any(r.id == rel.id for r in self.relations):
                self.relations.append(rel)

        return result

    def link_entry_resource(self, entry_id: str, resource_id: str, user_data: dict[str, Any]) -> ResourceEntry:
        """Create (or return existing) edge between an entry and a coarse resource."""
        where: dict[str, Any] = {
            "entry_id": entry_id,
            "resource_id": resource_id,
            **user_data,
        }
        with self._sessions.session() as session:
            stmt = select(self._resource_entry_model)
            filters = self._build_filters(self._resource_entry_model, where)
            if filters:
                stmt = stmt.where(*filters)
            existing = session.exec(stmt).first()

            if existing:
                return self._row_to_relation(existing)

            now = self._now()
            row = self._resource_entry_model(
                entry_id=entry_id,
                resource_id=resource_id,
                created_at=now,
                updated_at=now,
                **user_data,
            )
            session.add(row)
            session.commit()
            session.refresh(row)

        rel = self._row_to_relation(row)
        self.relations.append(rel)
        return rel

    def unlink_entry_resource(self, entry_id: str, resource_id: str) -> None:
        """Remove a single edge between an entry and a coarse resource."""
        with self._sessions.session() as session:
            stmt = select(self._resource_entry_model).where(
                self._resource_entry_model.entry_id == entry_id,
                self._resource_entry_model.resource_id == resource_id,
            )
            row = session.exec(stmt).first()
            if row:
                session.delete(row)
                session.commit()
                self.relations[:] = [
                    r for r in self.relations if not (r.entry_id == entry_id and r.resource_id == resource_id)
                ]

    def unlink_entry(self, entry_id: str) -> list[ResourceEntry]:
        """Remove all edges for a given entry (used on entry deletion)."""
        removed = self.list_relations({"entry_id": entry_id})
        if not removed:
            return []
        with self._sessions.session() as session:
            session.exec(delete(self._resource_entry_model).where(self._resource_entry_model.entry_id == entry_id))
            session.commit()
        self.relations[:] = [r for r in self.relations if r.entry_id != entry_id]
        return removed

    def clear_relations(self, where: Mapping[str, Any] | None = None) -> list[ResourceEntry]:
        """Remove all edges matching the scope (used on clear)."""
        removed = self.list_relations(where)
        if not removed:
            return []
        filters = self._build_filters(self._resource_entry_model, where)
        with self._sessions.session() as session:
            del_stmt = delete(self._resource_entry_model)
            if filters:
                del_stmt = del_stmt.where(*filters)
            session.exec(del_stmt)
            session.commit()
        removed_ids = {rel.id for rel in removed}
        self.relations[:] = [r for r in self.relations if r.id not in removed_ids]
        return removed

    def get_entry_resources(self, entry_id: str) -> list[ResourceEntry]:
        """Get all coarse-resource edges for a given entry."""
        return self.list_relations({"entry_id": entry_id})

    def load_existing(self) -> None:
        """Load all existing edges from database into cache."""
        self.list_relations()


__all__ = ["SQLiteResourceEntryRepo"]
