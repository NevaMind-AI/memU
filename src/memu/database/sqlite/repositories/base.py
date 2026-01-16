"""Base repository class for SQLite backend."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

import pendulum

from memu.database.sqlite.session import SQLiteSessionManager
from memu.database.state import DatabaseState

logger = logging.getLogger(__name__)


class SQLiteRepoBase:
    """Base class for SQLite repository implementations."""

    def __init__(
        self,
        *,
        state: DatabaseState,
        sqla_models: Any,
        sessions: SQLiteSessionManager,
        scope_fields: list[str],
    ) -> None:
        """Initialize base repository.

        Args:
            state: Shared database state for caching.
            sqla_models: SQLAlchemy model definitions.
            sessions: Session manager for database connections.
            scope_fields: List of user scope field names.
        """
        self._state = state
        self._sqla_models = sqla_models
        self._sessions = sessions
        self._scope_fields = scope_fields

    def _scope_kwargs_from(self, obj: Any) -> dict[str, Any]:
        """Extract scope fields from an object."""
        return {field: getattr(obj, field, None) for field in self._scope_fields}

    def _normalize_embedding(self, embedding: Any) -> list[float] | None:
        """Normalize embedding from various formats to list[float]."""
        if embedding is None:
            return None
        # Handle JSON string format (SQLite stores embeddings as JSON)
        if isinstance(embedding, str):
            try:
                return [float(x) for x in json.loads(embedding)]
            except (json.JSONDecodeError, TypeError):
                logger.debug("Could not parse embedding JSON: %s", embedding)
                return None
        # Handle list format
        try:
            return [float(x) for x in embedding]
        except (ValueError, TypeError, OverflowError):
            logger.debug("Could not normalize embedding %s", embedding)
            return None

    def _prepare_embedding(self, embedding: list[float] | None) -> str | None:
        """Serialize embedding to JSON string for SQLite storage."""
        if embedding is None:
            return None
        return json.dumps(embedding)

    def _merge_and_commit(self, obj: Any) -> None:
        """Merge object into session and commit."""
        with self._sessions.session() as session:
            session.merge(obj)
            session.commit()

    def _now(self) -> pendulum.DateTime:
        """Get current UTC time."""
        return pendulum.now("UTC")

    def _build_filters(self, model: Any, where: Mapping[str, Any] | None) -> list[Any]:
        """Build SQLAlchemy filter expressions from where clause."""
        if not where:
            return []
        filters: list[Any] = []
        for raw_key, expected in where.items():
            if expected is None:
                continue
            field, op = [*raw_key.split("__", 1), None][:2]
            column = getattr(model, str(field), None)
            if column is None:
                msg = f"Unknown filter field '{field}' for model '{model.__name__}'"
                raise ValueError(msg)
            if op == "in":
                if isinstance(expected, str):
                    filters.append(column == expected)
                else:
                    filters.append(column.in_(expected))
            else:
                filters.append(column == expected)
        return filters

    @staticmethod
    def _matches_where(obj: Any, where: Mapping[str, Any] | None) -> bool:
        """Check if object matches where clause (for in-memory filtering)."""
        if not where:
            return True
        for raw_key, expected in where.items():
            if expected is None:
                continue
            field, op = [*raw_key.split("__", 1), None][:2]
            actual = getattr(obj, str(field), None)
            if op == "in":
                if isinstance(expected, str):
                    if actual != expected:
                        return False
                else:
                    try:
                        if actual not in expected:
                            return False
                    except TypeError:
                        return False
            else:
                if actual != expected:
                    return False
        return True


__all__ = ["SQLiteRepoBase"]
