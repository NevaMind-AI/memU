"""SQLite database store implementation for MemU."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel
from sqlmodel import SQLModel

from memu.database.interfaces import Database
from memu.database.models import (
    RecallEntry,
    RecallFile,
    RecallFileEntry,
    RecallFileResource,
    RecallFileSegment,
    Resource,
)
from memu.database.repositories import (
    RecallEntryRepo,
    RecallFileEntryRepo,
    RecallFileRepo,
    RecallFileResourceRepo,
    RecallFileSegmentRepo,
    ResourceRepo,
)
from memu.database.sqlite.repositories.recall_entry_repo import SQLiteRecallEntryRepo
from memu.database.sqlite.repositories.recall_file_entry_repo import SQLiteRecallFileEntryRepo
from memu.database.sqlite.repositories.recall_file_repo import SQLiteRecallFileRepo
from memu.database.sqlite.repositories.recall_file_resource_repo import SQLiteRecallFileResourceRepo
from memu.database.sqlite.repositories.recall_file_segment_repo import SQLiteRecallFileSegmentRepo
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
        resource_repo: Repository for resource records.
        recall_file_repo: Repository for memory categories.
        recall_entry_repo: Repository for memory items.
        recall_file_entry_repo: Repository for category-item relations.
        resources: Dict cache of resource records.
        items: Dict cache of memory item records.
        categories: Dict cache of memory category records.
        relations: List cache of category-item relations.
    """

    resource_repo: ResourceRepo
    recall_file_repo: RecallFileRepo
    recall_entry_repo: RecallEntryRepo
    recall_file_entry_repo: RecallFileEntryRepo
    recall_file_resource_repo: RecallFileResourceRepo
    recall_file_segment_repo: RecallFileSegmentRepo
    resources: dict[str, Resource]
    items: dict[str, RecallEntry]
    categories: dict[str, RecallFile]
    relations: list[RecallFileEntry]
    resource_relations: list[RecallFileResource]
    segments: list[RecallFileSegment]

    def __init__(
        self,
        *,
        dsn: str,
        scope_model: type[BaseModel] | None = None,
        resource_model: type[Any] | None = None,
        recall_file_model: type[Any] | None = None,
        recall_entry_model: type[Any] | None = None,
        recall_file_entry_model: type[Any] | None = None,
        recall_file_resource_model: type[Any] | None = None,
        recall_file_segment_model: type[Any] | None = None,
        sqla_models: SQLiteSQLAModels | None = None,
    ) -> None:
        """Initialize SQLite database store.

        Args:
            dsn: SQLite connection string (e.g., "sqlite:///path/to/db.sqlite").
            scope_model: Pydantic model defining user scope fields.
            resource_model: Optional custom resource model.
            recall_file_model: Optional custom memory category model.
            recall_entry_model: Optional custom memory item model.
            recall_file_entry_model: Optional custom category-item model.
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
        recall_file_model = recall_file_model or self._sqla_models.RecallFile
        recall_entry_model = recall_entry_model or self._sqla_models.RecallEntry
        recall_file_entry_model = recall_file_entry_model or self._sqla_models.RecallFileEntry
        recall_file_resource_model = recall_file_resource_model or self._sqla_models.RecallFileResource
        recall_file_segment_model = recall_file_segment_model or self._sqla_models.RecallFileSegment

        # Initialize repositories
        self.resource_repo = SQLiteResourceRepo(
            state=self._state,
            resource_model=resource_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )
        self.recall_file_repo = SQLiteRecallFileRepo(
            state=self._state,
            recall_file_model=recall_file_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )
        self.recall_entry_repo = SQLiteRecallEntryRepo(
            state=self._state,
            recall_entry_model=recall_entry_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )
        self.recall_file_entry_repo = SQLiteRecallFileEntryRepo(
            state=self._state,
            recall_file_entry_model=recall_file_entry_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )
        self.recall_file_resource_repo = SQLiteRecallFileResourceRepo(
            state=self._state,
            recall_file_resource_model=recall_file_resource_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )
        self.recall_file_segment_repo = SQLiteRecallFileSegmentRepo(
            state=self._state,
            recall_file_segment_model=recall_file_segment_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )

        # Set up cache references
        self.resources = self._state.resources
        self.items = self._state.items
        self.categories = self._state.categories
        self.relations = self._state.relations
        self.resource_relations = self._state.resource_relations
        self.segments = self._state.segments

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
        self.recall_file_repo.load_existing()
        self.recall_entry_repo.load_existing()
        self.recall_file_entry_repo.load_existing()
        self.recall_file_resource_repo.load_existing()
        self.recall_file_segment_repo.load_existing()


__all__ = ["SQLiteStore"]
