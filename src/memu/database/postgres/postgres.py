from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from memu.database.interfaces import Database
from memu.database.models import RecallEntry, RecallFile, RecallFileEntry, Resource
from memu.database.postgres.migration import DDLMode, run_migrations
from memu.database.postgres.repositories.recall_entry_repo import PostgresRecallEntryRepo
from memu.database.postgres.repositories.recall_file_entry_repo import PostgresRecallFileEntryRepo
from memu.database.postgres.repositories.recall_file_repo import PostgresRecallFileRepo
from memu.database.postgres.repositories.resource_repo import PostgresResourceRepo
from memu.database.postgres.schema import SQLAModels, get_sqlalchemy_models, require_sqlalchemy
from memu.database.postgres.session import SessionManager
from memu.database.repositories import RecallEntryRepo, RecallFileEntryRepo, RecallFileRepo, ResourceRepo
from memu.database.state import DatabaseState

logger = logging.getLogger(__name__)


class PostgresStore(Database):
    resource_repo: ResourceRepo
    recall_file_repo: RecallFileRepo
    recall_entry_repo: RecallEntryRepo
    recall_file_entry_repo: RecallFileEntryRepo
    resources: dict[str, Resource]
    items: dict[str, RecallEntry]
    categories: dict[str, RecallFile]
    relations: list[RecallFileEntry]

    def __init__(
        self,
        *,
        dsn: str,
        ddl_mode: DDLMode = "create",
        vector_provider: str | None = None,
        scope_model: type[BaseModel] | None = None,
        base_model: type[BaseModel] | None = None,
        resource_model: type[Any] | None = None,
        recall_file_model: type[Any] | None = None,
        recall_entry_model: type[Any] | None = None,
        recall_file_entry_model: type[Any] | None = None,
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
        recall_file_model = recall_file_model or self._sqla_models.RecallFile
        recall_entry_model = recall_entry_model or self._sqla_models.RecallEntry
        recall_file_entry_model = recall_file_entry_model or self._sqla_models.RecallFileEntry

        self.resource_repo = PostgresResourceRepo(
            state=self._state,
            resource_model=resource_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )
        self.recall_file_repo = PostgresRecallFileRepo(
            state=self._state,
            recall_file_model=recall_file_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )
        self.recall_entry_repo = PostgresRecallEntryRepo(
            state=self._state,
            recall_entry_model=recall_entry_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
            use_vector=self._use_vector_type,
        )
        self.recall_file_entry_repo = PostgresRecallFileEntryRepo(
            state=self._state,
            recall_file_entry_model=recall_file_entry_model,
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
        self.recall_file_repo.load_existing()
        self.recall_entry_repo.load_existing()
        self.recall_file_entry_repo.load_existing()
