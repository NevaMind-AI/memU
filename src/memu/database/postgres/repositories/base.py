"""Base repository class for PostgreSQL backend."""

from __future__ import annotations

import logging
from typing import Any

from memu.database.base import RepoBaseMixin
from memu.database.postgres.session import SessionManager
from memu.database.state import DatabaseState

logger = logging.getLogger(__name__)


class PostgresRepoBase(RepoBaseMixin):
    """Base class for PostgreSQL repository implementations.

    Inherits common functionality from RepoBaseMixin and provides
    PostgreSQL-specific embedding normalization for pgvector type.
    """

    def __init__(
        self,
        *,
        state: DatabaseState,
        sqla_models: Any,
        sessions: SessionManager,
        scope_fields: list[str],
        use_vector: bool = True,
    ) -> None:
        """Initialize base repository.

        Args:
            state: Shared database state for caching.
            sqla_models: SQLAlchemy model definitions.
            sessions: Session manager for database connections.
            scope_fields: List of user scope field names.
            use_vector: Whether to use vector operations (default: True).
        """
        self._state = state
        self._sqla_models = sqla_models
        self._sessions = sessions
        self._scope_fields = scope_fields
        self._use_vector = use_vector

    def _normalize_embedding(self, embedding: Any) -> list[float] | None:
        """Normalize embedding from various formats to list[float].

        PostgreSQL with pgvector stores embeddings as vector objects that
        may have a to_list() method, or as string representations.

        Args:
            embedding: Embedding in various formats (pgvector, str, list, or None).

        Returns:
            Normalized embedding as list of floats, or None if invalid.

        Note:
            This is PostgreSQL-specific due to pgvector type handling.
            SQLite uses JSON storage with a different normalization approach.
        """
        if embedding is None:
            return None
        # Handle pgvector objects with to_list method
        if hasattr(embedding, "to_list"):
            try:
                return [float(x) for x in embedding.to_list()]
            except Exception:
                logger.debug("Could not convert pgvector value %s", embedding)
                return None
        # Handle string representation (e.g., "[0.1, 0.2, 0.3]")
        if isinstance(embedding, str):
            stripped = embedding.strip("[]")
            if not stripped:
                return []
            return [float(x) for x in stripped.split(",")]
        # Handle list format
        try:
            return [float(x) for x in embedding]
        except Exception:
            logger.debug("Could not normalize embedding %s", embedding)
            return None

    def _prepare_embedding(self, embedding: list[float] | None) -> Any:
        """Prepare embedding for PostgreSQL storage.

        Args:
            embedding: Embedding as list of floats or None.

        Returns:
            Embedding ready for pgvector storage, or None.

        Note:
            This is PostgreSQL-specific. pgvector accepts lists directly.
            SQLite requires JSON serialization.
        """
        if embedding is None:
            return None
        return embedding


__all__ = ["PostgresRepoBase"]
