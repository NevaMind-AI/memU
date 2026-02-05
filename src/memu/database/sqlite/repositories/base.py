"""Base repository class for SQLite backend."""

from __future__ import annotations

import json
import logging
from typing import Any

from memu.database.base import RepoBaseMixin
from memu.database.sqlite.session import SQLiteSessionManager
from memu.database.state import DatabaseState

logger = logging.getLogger(__name__)


class SQLiteRepoBase(RepoBaseMixin):
    """Base class for SQLite repository implementations.

    Inherits common functionality from RepoBaseMixin and provides
    SQLite-specific embedding normalization methods.
    """

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

    def _normalize_embedding(self, embedding: Any) -> list[float] | None:
        """Normalize embedding from various formats to list[float].

        SQLite stores embeddings as JSON strings, so this method handles
        JSON deserialization in addition to standard list formats.

        Args:
            embedding: Embedding in various formats (str, list, or None).

        Returns:
            Normalized embedding as list of floats, or None if invalid.

        Note:
            This is SQLite-specific due to JSON storage format.
            PostgreSQL uses pgvector with a different normalization approach.
        """
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
        """Serialize embedding to JSON string for SQLite storage.

        Args:
            embedding: Embedding as list of floats or None.

        Returns:
            JSON string representation of embedding, or None.

        Note:
            This is SQLite-specific. PostgreSQL stores embeddings directly
            using the pgvector type.
        """
        if embedding is None:
            return None
        return json.dumps(embedding)


__all__ = ["SQLiteRepoBase"]
