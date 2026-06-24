"""SQLite entry repository implementation."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import pendulum
from sqlalchemy import func
from sqlmodel import delete, select

from memu.database.models import Entry, compute_content_hash
from memu.database.repositories.entry import EntryRepo
from memu.database.sqlite.repositories.base import SQLiteRepoBase
from memu.database.sqlite.schema import SQLiteSQLAModels
from memu.database.sqlite.session import SQLiteSessionManager
from memu.database.state import DatabaseState
from memu.vector import cosine_topk, cosine_topk_salience

logger = logging.getLogger(__name__)


class SQLiteEntryRepo(SQLiteRepoBase, EntryRepo):
    """SQLite implementation of the entry repository (the searchable atoms)."""

    def __init__(
        self,
        *,
        state: DatabaseState,
        entry_model: type[Any],
        sqla_models: SQLiteSQLAModels,
        sessions: SQLiteSessionManager,
        scope_fields: list[str],
    ) -> None:
        """Initialize entry repository.

        Args:
            state: Shared database state for caching.
            entry_model: SQLModel class for entries.
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
        self._entry_model = entry_model
        self.entries = self._state.entries

    def _row_to_entry(self, row: Any) -> Entry:
        """Map an ORM row to a backend-agnostic Entry record."""
        return Entry(
            id=row.id,
            lane=row.lane,
            source_id=row.source_id,
            source_path=row.source_path,
            entry_type=row.entry_type,
            text=row.text,
            embedding=self._normalize_embedding(row.embedding),
            happened_at=row.happened_at,
            extra=row.extra or {},
            created_at=row.created_at,
            updated_at=row.updated_at,
            **self._scope_kwargs_from(row),
        )

    def get_entry(self, entry_id: str) -> Entry | None:
        """Get an entry by ID."""
        if entry_id in self.entries:
            return self.entries[entry_id]

        with self._sessions.session() as session:
            stmt = select(self._entry_model).where(self._entry_model.id == entry_id)
            row = session.exec(stmt).first()

        if row is None:
            return None

        entry = self._row_to_entry(row)
        self.entries[row.id] = entry
        return entry

    def list_entries(self, where: Mapping[str, Any] | None = None, *, lane: str | None = None) -> dict[str, Entry]:
        """List entries matching the where clause and optional lane filter."""
        filters = self._build_filters(self._entry_model, where)
        filters.extend(self._lane_filters(self._entry_model, lane))
        with self._sessions.session() as session:
            stmt = select(self._entry_model)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.exec(stmt).all()

        result: dict[str, Entry] = {}
        for row in rows:
            entry = self._row_to_entry(row)
            result[row.id] = entry
            self.entries[row.id] = entry

        return result

    def list_entries_by_ref_ids(self, ref_ids: list[str], where: Mapping[str, Any] | None = None) -> dict[str, Entry]:
        """List entries whose ``extra.ref_id`` is in ``ref_ids``."""
        if not ref_ids:
            return {}

        with self._sessions.session() as session:
            stmt = select(self._entry_model)
            filters = self._build_filters(self._entry_model, where)
            ref_id_col = func.json_extract(self._entry_model.extra, "$.ref_id")
            filters.append(ref_id_col.isnot(None))
            filters.append(ref_id_col.in_(ref_ids))
            if filters:
                stmt = stmt.where(*filters)
            rows = session.exec(stmt).all()

        result: dict[str, Entry] = {}
        for row in rows:
            entry = self._row_to_entry(row)
            result[row.id] = entry
            self.entries[row.id] = entry

        return result

    def clear_entries(self, where: Mapping[str, Any] | None = None, *, lane: str | None = None) -> dict[str, Entry]:
        """Clear entries matching the where clause and optional lane filter."""
        filters = self._build_filters(self._entry_model, where)
        filters.extend(self._lane_filters(self._entry_model, lane))
        with self._sessions.session() as session:
            stmt = select(self._entry_model)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.exec(stmt).all()

            deleted: dict[str, Entry] = {row.id: self._row_to_entry(row) for row in rows}

            if not deleted:
                return {}

            del_stmt = delete(self._entry_model)
            if filters:
                del_stmt = del_stmt.where(*filters)
            session.exec(del_stmt)
            session.commit()

        for entry_id in deleted:
            self.entries.pop(entry_id, None)

        return deleted

    def create_entry(
        self,
        *,
        lane: str,
        source_id: str | None,
        entry_type: str,
        text: str,
        embedding: list[float],
        user_data: dict[str, Any],
        source_path: str | None = None,
        reinforce: bool = False,
    ) -> Entry:
        """Create a new entry (optionally reinforcing a duplicate)."""
        if reinforce:
            return self.create_entry_reinforce(
                lane=lane,
                source_id=source_id,
                entry_type=entry_type,
                text=text,
                embedding=embedding,
                user_data=user_data,
                source_path=source_path,
            )

        now = self._now()
        row = self._entry_model(
            lane=lane,
            source_id=source_id,
            source_path=source_path,
            entry_type=entry_type,
            text=text,
            embedding=self._prepare_embedding(embedding),
            extra={},
            created_at=now,
            updated_at=now,
            **user_data,
        )
        with self._sessions.session() as session:
            session.add(row)
            session.commit()
            session.refresh(row)

        entry = self._row_to_entry(row)
        self.entries[row.id] = entry
        return entry

    def create_entry_reinforce(
        self,
        *,
        lane: str,
        source_id: str | None,
        entry_type: str,
        text: str,
        embedding: list[float],
        user_data: dict[str, Any],
        source_path: str | None = None,
    ) -> Entry:
        """Create or reinforce an entry with content-hash deduplication.

        If an entry with the same content hash exists in the same scope, reinforce
        it instead of creating a duplicate.
        """
        content_hash = compute_content_hash(text, entry_type)

        with self._sessions.session() as session:
            content_hash_col = func.json_extract(self._entry_model.extra, "$.content_hash")
            filters = [content_hash_col == content_hash]
            filters.extend(self._build_filters(self._entry_model, user_data))

            existing = session.exec(select(self._entry_model).where(*filters)).first()

            if existing:
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

                entry = self._row_to_entry(existing)
                self.entries[existing.id] = entry
                return entry

            now = self._now()
            entry_extra = user_data.pop("extra", {}) if "extra" in user_data else {}
            entry_extra.update({
                "content_hash": content_hash,
                "reinforcement_count": 1,
                "last_reinforced_at": now.isoformat(),
            })

            row = self._entry_model(
                lane=lane,
                source_id=source_id,
                source_path=source_path,
                entry_type=entry_type,
                text=text,
                embedding=self._prepare_embedding(embedding),
                extra=entry_extra,
                created_at=now,
                updated_at=now,
                **user_data,
            )
            session.add(row)
            session.commit()
            session.refresh(row)

        entry = self._row_to_entry(row)
        self.entries[row.id] = entry
        return entry

    def update_entry(
        self,
        *,
        entry_id: str,
        entry_type: str | None = None,
        text: str | None = None,
        embedding: list[float] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> Entry:
        """Update an existing entry.

        Raises:
            KeyError: If the entry is not found.
        """
        with self._sessions.session() as session:
            stmt = select(self._entry_model).where(self._entry_model.id == entry_id)
            row = session.exec(stmt).first()

            if row is None:
                msg = f"Entry with id {entry_id} not found"
                raise KeyError(msg)

            if entry_type is not None:
                row.entry_type = entry_type
            if text is not None:
                row.text = text
            if embedding is not None:
                row.embedding = self._prepare_embedding(embedding)

            if extra is not None:
                row.extra = {**(row.extra or {}), **extra}

            row.updated_at = self._now()

            session.add(row)
            session.commit()
            session.refresh(row)

        entry = self._row_to_entry(row)
        self.entries[row.id] = entry
        return entry

    def delete_entry(self, entry_id: str) -> None:
        """Delete an entry by id."""
        with self._sessions.session() as session:
            stmt = select(self._entry_model).where(self._entry_model.id == entry_id)
            row = session.exec(stmt).first()
            if row:
                session.delete(row)
                session.commit()

        self.entries.pop(entry_id, None)

    def vector_search_entries(
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
        *,
        lane: str | None = None,
        ranking: str = "similarity",
        recency_decay_days: float = 30.0,
    ) -> list[tuple[str, float]]:
        """Rank entries by brute-force cosine similarity or salience.

        SQLite has no native vector support, so embeddings are scored in Python.
        """
        pool = self.list_entries(where, lane=lane)

        if ranking == "salience":
            corpus = [
                (
                    e.id,
                    e.embedding,
                    (e.extra or {}).get("reinforcement_count", 1),
                    self._parse_datetime((e.extra or {}).get("last_reinforced_at")),
                )
                for e in pool.values()
            ]
            return cosine_topk_salience(query_vec, corpus, k=top_k, recency_decay_days=recency_decay_days)

        return cosine_topk(query_vec, [(e.id, e.embedding) for e in pool.values()], k=top_k)

    @staticmethod
    def _parse_datetime(dt_str: str | None) -> pendulum.DateTime | None:
        """Parse an ISO datetime string from the extra dict."""
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
        """Load all existing entries from database into cache."""
        self.list_entries()


__all__ = ["SQLiteEntryRepo"]
