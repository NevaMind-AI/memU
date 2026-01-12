from __future__ import annotations

import contextlib
import logging
from typing import Any

from pydantic import BaseModel

from memu.database.interfaces import Database
from memu.database.models import CategoryItem, MemoryCategory, MemoryItem, Resource
from memu.database.oracle.repositories.category_item_repo import OracleCategoryItemRepo
from memu.database.oracle.repositories.memory_category_repo import OracleMemoryCategoryRepo
from memu.database.oracle.repositories.memory_item_repo import OracleMemoryItemRepo
from memu.database.oracle.repositories.resource_repo import OracleResourceRepo
from memu.database.oracle.schema import SQLAModels, get_metadata, get_sqlalchemy_models, require_sqlalchemy
from memu.database.oracle.session import SessionManager
from memu.database.repositories import CategoryItemRepo, MemoryCategoryRepo, MemoryItemRepo, ResourceRepo
from memu.database.state import DatabaseState

with contextlib.suppress(ImportError):
    from sqlalchemy import create_engine

logger = logging.getLogger(__name__)


class OracleStorage(Database):
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
        ddl_mode: str = "create",
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
        # Force oracle+oracledb driver
        if dsn.startswith("oracle://"):
            dsn = dsn.replace("oracle://", "oracle+oracledb://", 1)
        elif not dsn.startswith("oracle+oracledb://"):
            # If it doesn't have a protocol or has another one, we might want to warn or correct,
            # but for now let's just assume if it looks like a DSN we try to ensure the driver is there
            # if the user intended generic oracle.
            # However, safer to just update if it is 'oracle://' or leave it if it is already correct.
            pass

        self.dsn = dsn
        self.ddl_mode = ddl_mode
        self.vector_provider = vector_provider
        self._use_vector_type = False  # Disabled by default for Oracle initial version
        self._scope_model: type[BaseModel] = scope_model or base_model or BaseModel
        self._scope_fields = list(getattr(self._scope_model, "model_fields", {}).keys())
        self._state = DatabaseState()
        self._sessions = SessionManager(dsn=self.dsn)
        self._sqla_models: SQLAModels = sqla_models or get_sqlalchemy_models(scope_model=self._scope_model)

        # Inline minimal migration/ddl handling to avoid external dependency on alembic/migrations
        self._ensure_schema()

        resource_model = resource_model or self._sqla_models.Resource
        memory_category_model = memory_category_model or self._sqla_models.MemoryCategory
        memory_item_model = memory_item_model or self._sqla_models.MemoryItem
        category_item_model = category_item_model or self._sqla_models.CategoryItem

        self.resource_repo = OracleResourceRepo(
            state=self._state,
            resource_model=resource_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )
        self.memory_category_repo = OracleMemoryCategoryRepo(
            state=self._state,
            memory_category_model=memory_category_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )
        self.memory_item_repo = OracleMemoryItemRepo(
            state=self._state,
            memory_item_model=memory_item_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
            use_vector=self._use_vector_type,
        )
        self.category_item_repo = OracleCategoryItemRepo(
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

    def _ensure_schema(self) -> None:
        """Create tables if they don't exist."""
        if self.ddl_mode == "create":
            metadata = get_metadata(self._scope_model)
            engine = create_engine(self.dsn)
            metadata.create_all(engine)
            engine.dispose()

    def close(self) -> None:
        self._sessions.close()

    def _load_existing(self) -> None:
        self.resource_repo.load_existing()
        self.memory_category_repo.load_existing()
        self.memory_item_repo.load_existing()
        self.category_item_repo.load_existing()


def build_oracle_database(
    config: Any,
    user_model: type[BaseModel],
) -> Database:
    """Builder function for factory."""
    metadata = config.metadata_store

    return OracleStorage(
        dsn=metadata.dsn,
        ddl_mode=metadata.ddl_mode,
        vector_provider=metadata.vector_provider,
        scope_model=user_model,
    )
