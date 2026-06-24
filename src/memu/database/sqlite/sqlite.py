"""SQLite database store implementation for MemU."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel
from sqlmodel import SQLModel

from memu.database.interfaces import Database
from memu.database.models import Entry, Resource, ResourceEntry
from memu.database.repositories import EntryRepo, ResourceEntryRepo, ResourceRepo
from memu.database.sqlite.repositories.entry_repo import SQLiteEntryRepo
from memu.database.sqlite.repositories.resource_entry_repo import SQLiteResourceEntryRepo
from memu.database.sqlite.repositories.resource_repo import SQLiteResourceRepo
from memu.database.sqlite.schema import SQLiteSQLAModels, get_sqlite_sqlalchemy_models
from memu.database.sqlite.session import SQLiteSessionManager
from memu.database.state import DatabaseState

logger = logging.getLogger(__name__)


class SQLiteStore(Database):
    """SQLite database store implementation.

    This store provides a lightweight, file-based database backend for MemU.
    It uses SQLite for metadata storage and brute-force cosine similarity
    for vector search (native vector support is not available in SQLite).

    Attributes:
        resource_repo: Repository for resource records (raw inputs and lane docs).
        entry_repo: Repository for lane entries (the searchable atoms).
        resource_entry_repo: Repository for entry <-> resource membership edges.
        resources: Dict cache of resource records.
        entries: Dict cache of entry records.
        relations: List cache of membership edges.
    """

    resource_repo: ResourceRepo
    entry_repo: EntryRepo
    resource_entry_repo: ResourceEntryRepo
    resources: dict[str, Resource]
    entries: dict[str, Entry]
    relations: list[ResourceEntry]

    def __init__(
        self,
        *,
        dsn: str,
        scope_model: type[BaseModel] | None = None,
        resource_model: type[Any] | None = None,
        entry_model: type[Any] | None = None,
        resource_entry_model: type[Any] | None = None,
        sqla_models: SQLiteSQLAModels | None = None,
    ) -> None:
        """Initialize SQLite database store.

        Args:
            dsn: SQLite connection string (e.g., "sqlite:///path/to/db.sqlite").
            scope_model: Pydantic model defining user scope fields.
            resource_model: Optional custom resource table model.
            entry_model: Optional custom entry table model.
            resource_entry_model: Optional custom membership-edge table model.
            sqla_models: Pre-built SQLAlchemy models container.
        """
        self.dsn = dsn
        self._scope_model: type[BaseModel] = scope_model or BaseModel
        self._scope_fields = list(getattr(self._scope_model, "model_fields", {}).keys())
        self._state = DatabaseState()
        self._sessions = SQLiteSessionManager(dsn=self.dsn)
        self._sqla_models: SQLiteSQLAModels = sqla_models or get_sqlite_sqlalchemy_models(scope_model=self._scope_model)

        # Create tables
        self._create_tables()

        # Use provided models or defaults from sqla_models
        resource_model = resource_model or self._sqla_models.Resource
        entry_model = entry_model or self._sqla_models.Entry
        resource_entry_model = resource_entry_model or self._sqla_models.ResourceEntry

        # Initialize repositories
        self.resource_repo = SQLiteResourceRepo(
            state=self._state,
            resource_model=resource_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )
        self.entry_repo = SQLiteEntryRepo(
            state=self._state,
            entry_model=entry_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )
        self.resource_entry_repo = SQLiteResourceEntryRepo(
            state=self._state,
            resource_entry_model=resource_entry_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )

        # Set up cache references
        self.resources = self._state.resources
        self.entries = self._state.entries
        self.relations = self._state.relations

    def _create_tables(self) -> None:
        """Create SQLite tables if they don't exist."""
        SQLModel.metadata.create_all(self._sessions.engine)
        # Also create tables from our custom metadata
        self._sqla_models.Base.metadata.create_all(self._sessions.engine)
        logger.debug("SQLite tables created/verified")

    def close(self) -> None:
        """Close the database connection and release resources."""
        self._sessions.close()

    def load_existing(self) -> None:
        """Load all existing data from database into cache."""
        self.resource_repo.load_existing()
        self.entry_repo.load_existing()
        self.resource_entry_repo.load_existing()


__all__ = ["SQLiteStore"]
