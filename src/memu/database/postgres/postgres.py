from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from memu.database.interfaces import Database
from memu.database.models import (
    RecallFile,
    RecallFileResource,
    RecallFileSegment,
    Resource,
)
from memu.database.postgres.migration import DDLMode, run_migrations
from memu.database.postgres.repositories.recall_file_repo import PostgresRecallFileRepo
from memu.database.postgres.repositories.recall_file_resource_repo import PostgresRecallFileResourceRepo
from memu.database.postgres.repositories.recall_file_segment_repo import PostgresRecallFileSegmentRepo
from memu.database.postgres.repositories.resource_repo import PostgresResourceRepo
from memu.database.postgres.schema import SQLAModels, get_sqlalchemy_models, require_sqlalchemy
from memu.database.postgres.session import SessionManager
from memu.database.repositories import (
    RecallFileRepo,
    RecallFileResourceRepo,
    RecallFileSegmentRepo,
    ResourceRepo,
)
from memu.database.state import DatabaseState

logger = logging.getLogger(__name__)


class PostgresStore(Database):
    resource_repo: ResourceRepo
    recall_file_repo: RecallFileRepo
    recall_file_resource_repo: RecallFileResourceRepo
    recall_file_segment_repo: RecallFileSegmentRepo
    resources: dict[str, Resource]
    categories: dict[str, RecallFile]
    resource_relations: list[RecallFileResource]
    segments: list[RecallFileSegment]

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
        recall_file_resource_model: type[Any] | None = None,
        recall_file_segment_model: type[Any] | None = None,
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
        recall_file_resource_model = recall_file_resource_model or self._sqla_models.RecallFileResource
        recall_file_segment_model = recall_file_segment_model or self._sqla_models.RecallFileSegment

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
        self.recall_file_resource_repo = PostgresRecallFileResourceRepo(
            state=self._state,
            recall_file_resource_model=recall_file_resource_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )
        self.recall_file_segment_repo = PostgresRecallFileSegmentRepo(
            state=self._state,
            recall_file_segment_model=recall_file_segment_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
        )

        self.resources = self._state.resources
        self.categories = self._state.categories
        self.resource_relations = self._state.resource_relations
        self.segments = self._state.segments

        # self._load_existing()

    def close(self) -> None:
        self._sessions.close()

    def _load_existing(self) -> None:
        self.resource_repo.load_existing()
        self.recall_file_repo.load_existing()
        self.recall_file_resource_repo.load_existing()
        self.recall_file_segment_repo.load_existing()
