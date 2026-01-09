"""SQLite session manager for database connections."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, create_engine

logger = logging.getLogger(__name__)


class SQLiteSessionManager:
    """Handle engine lifecycle and session creation for SQLite store."""

    def __init__(self, *, dsn: str, engine_kwargs: dict[str, Any] | None = None) -> None:
        """Initialize SQLite session manager.

        Args:
            dsn: SQLite connection string (e.g., "sqlite:///path/to/db.sqlite").
            engine_kwargs: Optional keyword arguments for create_engine.
        """
        kw: dict[str, Any] = {
            "connect_args": {"check_same_thread": False},  # Allow multi-threaded access
        }
        if engine_kwargs:
            kw.update(engine_kwargs)
        self._engine = create_engine(dsn, **kw)

    def session(self) -> Session:
        """Create a new database session."""
        return Session(self._engine, expire_on_commit=False)

    def close(self) -> None:
        """Close the database engine and release resources."""
        try:
            self._engine.dispose()
        except SQLAlchemyError:
            logger.exception("Failed to close SQLite engine")

    @property
    def engine(self) -> Any:
        """Return the underlying SQLAlchemy engine."""
        return self._engine


__all__ = ["SQLiteSessionManager"]
