"""SQLite database store implementation for MemU."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel
from sqlmodel import SQLModel

from memu.database.interfaces import Database
from memu.database.models import CategoryItem, MemoryCategory, MemoryItem, Resource
from memu.database.repositories import CategoryItemRepo, MemoryCategoryRepo, MemoryItemRepo, ResourceRepo
from memu.database.sqlite.repositories.category_item_repo import SQLiteCategoryItemRepo
from memu.database.sqlite.repositories.memory_category_repo import SQLiteMemoryCategoryRepo
from memu.database.sqlite.repositories.memory_item_repo import SQLiteMemoryItemRepo
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
        memory_category_repo: Repository for memory categories.
        memory_item_repo: Repository for memory items.
        category_item_repo: Repository for category-item relations.
        resources: Dict cache of resource records.
        items: Dict cache of memory item records.
        categories: Dict cache of memory category records.
        relations: List cache of category-item relations.
    """

    resource_repo: ResourceRepo
    memory_category_repo: MemoryCategoryRepo
    memory_item_repo: MemoryItemRepo
    category_item_repo: CategoryItemRepo
    resources: dict[str, Resource]
    items: dict[str, MemoryItem]
    categories: dict[str, MemoryCategory]
    relations: list[CategoryItem]

    def __init__(
        self,
        *,
        dsn: str,
        scope_model: type[BaseModel] | None = None,
        resource_model: type[Any] | None = None,
        memory_category_model: type[Any] | None = None,
        memory_item_model: type[Any] | None = None,
        category_item_model: type[Any] | None = None,
        sqla_models: SQLiteSQLAModels | None = None,
    ) -> None:
        """Initialize SQLite database store.

        Args:
            dsn: SQLite connection string (e.g., "sqlite:///path/to/db.sqlite").
            scope_model: Pydantic model defining user scope fields.
            resource_model: Optional custom resource model.
            memory_category_model: Optional custom memory category model.
            memory_item_model: Optional custom memory item model.
            category_item_model: Optional custom category-item model.
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
        memory_category_model = memory_category_model or self._sqla_models.MemoryCategory
        memory_item_model = memory_item_model or self._sqla_models.MemoryItem
        category_item_model = category_item_model or self._sqla_models.CategoryItem

        # Initialize repositories
        self.resource_repo = SQLiteResourceRepo(
            state=self._state,
            resource_model=resource_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )
        self.memory_category_repo = SQLiteMemoryCategoryRepo(
            state=self._state,
            memory_category_model=memory_category_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )
        self.memory_item_repo = SQLiteMemoryItemRepo(
            state=self._state,
            memory_item_model=memory_item_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )
        self.category_item_repo = SQLiteCategoryItemRepo(
            state=self._state,
            category_item_model=category_item_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )

        # Set up cache references
        self.resources = self._state.resources
        self.items = self._state.items
        self.categories = self._state.categories
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
        self.memory_category_repo.load_existing()
        self.memory_item_repo.load_existing()
        self.category_item_repo.load_existing()


__all__ = ["SQLiteStore"]
