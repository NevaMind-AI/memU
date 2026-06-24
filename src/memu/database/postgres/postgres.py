from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from memu.database.interfaces import Database
from memu.database.models import Entry, Resource, ResourceEntry
from memu.database.postgres.migration import DDLMode, run_migrations
from memu.database.postgres.repositories.entry_repo import PostgresEntryRepo
from memu.database.postgres.repositories.resource_entry_repo import PostgresResourceEntryRepo
from memu.database.postgres.repositories.resource_repo import PostgresResourceRepo
from memu.database.postgres.schema import SQLAModels, get_sqlalchemy_models, require_sqlalchemy
from memu.database.postgres.session import SessionManager
from memu.database.repositories import EntryRepo, ResourceEntryRepo, ResourceRepo
from memu.database.state import DatabaseState

logger = logging.getLogger(__name__)


class PostgresStore(Database):
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
        ddl_mode: DDLMode = "create",
        vector_provider: str | None = None,
        scope_model: type[BaseModel] | None = None,
        base_model: type[BaseModel] | None = None,
        resource_model: type[Any] | None = None,
        entry_model: type[Any] | None = None,
        resource_entry_model: type[Any] | None = None,
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
        entry_model = entry_model or self._sqla_models.Entry
        resource_entry_model = resource_entry_model or self._sqla_models.ResourceEntry

        self.resource_repo = PostgresResourceRepo(
            state=self._state,
            resource_model=resource_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
            use_vector=self._use_vector_type,
        )
        self.entry_repo = PostgresEntryRepo(
            state=self._state,
            entry_model=entry_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
            use_vector=self._use_vector_type,
        )
        self.resource_entry_repo = PostgresResourceEntryRepo(
            state=self._state,
            resource_entry_model=resource_entry_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )

        self.resources = self._state.resources
        self.entries = self._state.entries
        self.relations = self._state.relations

    def close(self) -> None:
        self._sessions.close()
