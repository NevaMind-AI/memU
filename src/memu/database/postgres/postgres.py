from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from memu.database.interfaces import Database
from memu.database.models import CategoryItem, MemoryCategory, MemoryItem, Resource
from memu.database.postgres.migration import DDLMode, run_migrations
from memu.database.postgres.repositories.category_item_repo import PostgresCategoryItemRepo
from memu.database.postgres.repositories.memory_category_repo import PostgresMemoryCategoryRepo
from memu.database.postgres.repositories.memory_item_repo import PostgresMemoryItemRepo
from memu.database.postgres.repositories.resource_repo import PostgresResourceRepo
from memu.database.postgres.schema import SQLAModels, get_sqlalchemy_models, require_sqlalchemy
from memu.database.postgres.session import SessionManager
from memu.database.repositories import CategoryItemRepo, MemoryCategoryRepo, MemoryItemRepo, ResourceRepo
from memu.database.state import DatabaseState

logger = logging.getLogger(__name__)


class PostgresStore(Database):
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
        ddl_mode: DDLMode = "create",
        vector_provider: str | None = None,
        scope_model: type[BaseModel] | None = None,
        base_model: type[BaseModel] | None = None,
        resource_model: type[Any] | None = None,
        memory_category_model: type[Any] | None = None,
        memory_item_model: type[Any] | None = None,
        category_item_model: type[Any] | None = None,
        sqla_models: SQLAModels | None = None,
    ) -> None:
        require_sqlalchemy()
        self.dsn = dsn
        self.ddl_mode = ddl_mode
        self.vector_provider = vector_provider
        self._use_vector_type = vector_provider == "pgvector"
        self._scope_model: type[BaseModel] = scope_model or base_model or BaseModel
        self._scope_fields = list(getattr(self._scope_model, "model_fields", {}).keys())
        self._state = DatabaseState()
        self._sessions = SessionManager(dsn=self.dsn)
        self._sqla_models: SQLAModels = sqla_models or get_sqlalchemy_models(scope_model=self._scope_model)
        run_migrations(dsn=self.dsn, scope_model=self._scope_model, ddl_mode=self.ddl_mode)

        resource_model = resource_model or self._sqla_models.Resource
        memory_category_model = memory_category_model or self._sqla_models.MemoryCategory
        memory_item_model = memory_item_model or self._sqla_models.MemoryItem
        category_item_model = category_item_model or self._sqla_models.CategoryItem

        self.resource_repo = PostgresResourceRepo(
            state=self._state,
            resource_model=resource_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )
        self.memory_category_repo = PostgresMemoryCategoryRepo(
            state=self._state,
            memory_category_model=memory_category_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )
        self.memory_item_repo = PostgresMemoryItemRepo(
            state=self._state,
            memory_item_model=memory_item_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
            use_vector=self._use_vector_type,
        )
        self.category_item_repo = PostgresCategoryItemRepo(
            state=self._state,
            category_item_model=category_item_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )

        self.resources = self._state.resources
        self.items = self._state.items
        self.categories = self._state.categories
        self.relations = self._state.relations

        # self._load_existing()

    def close(self) -> None:
        self._sessions.close()

    def _load_existing(self) -> None:
        self.resource_repo.load_existing()
        self.memory_category_repo.load_existing()
        self.memory_item_repo.load_existing()
        self.category_item_repo.load_existing()
