from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, cast

from pydantic import BaseModel
from sqlalchemy import select, text, update

from memu.database.interfaces import Database, EmbeddingSpaceMismatch
from memu.database.models import (
    RecallFile,
    RecallFileSegment,
    Resource,
)
from memu.database.postgres.migration import DDLMode, run_migrations
from memu.database.postgres.repositories.recall_file_repo import PostgresRecallFileRepo
from memu.database.postgres.repositories.recall_file_segment_repo import PostgresRecallFileSegmentRepo
from memu.database.postgres.repositories.resource_repo import PostgresResourceRepo
from memu.database.postgres.schema import SQLAModels, get_sqlalchemy_models, require_sqlalchemy
from memu.database.postgres.session import SessionManager
from memu.database.repositories import (
    RecallFileRepo,
    RecallFileSegmentRepo,
    ResourceRepo,
)
from memu.database.state import DatabaseState

logger = logging.getLogger(__name__)
_REINDEX_CONFLICT = "record changed during embedding reindex"


class PostgresStore(Database):
    resource_repo: ResourceRepo
    recall_file_repo: RecallFileRepo
    recall_file_segment_repo: RecallFileSegmentRepo
    resources: dict[str, Resource]
    recall_files: dict[str, RecallFile]
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
        self.recall_file_segment_repo = PostgresRecallFileSegmentRepo(
            state=self._state,
            recall_file_segment_model=recall_file_segment_model,
            sqla_models=self._sqla_models,
            sessions=self._sessions,
            scope_fields=self._scope_fields,
            # Honour an explicit non-pgvector ``vector_index.provider``: the column
            # type is ``VECTOR`` regardless, but a deployment that asked for
            # brute force gets brute force.
            use_vector=self._use_vector_type,
        )

        self.resources = self._state.resources
        self.recall_files = self._state.recall_files
        self.segments = self._state.segments

        # self._load_existing()

    def close(self) -> None:
        self._sessions.close()

    def _load_existing(self) -> None:
        self.resource_repo.load_existing()
        self.recall_file_repo.load_existing()
        self.recall_file_segment_repo.load_existing()

    def assert_embedding_space(self, embedding_space: str, *, initialize: bool = True) -> None:
        with self._sessions.session() as session:
            current = session.execute(
                text("SELECT identity FROM memu_embedding_space WHERE id = 1")
            ).scalar_one_or_none()
            if current == embedding_space:
                self._state.embedding_space = embedding_space
                self._state.expected_embedding_space = embedding_space
                return
            has_vectors = any(
                session.execute(select(model.id).where(model.embedding.is_not(None)).limit(1)).first()
                for model in (
                    self._sqla_models.Resource,
                    self._sqla_models.RecallFile,
                    self._sqla_models.RecallFileSegment,
                )
            )
            if has_vectors and current != embedding_space:
                raise EmbeddingSpaceMismatch
            if initialize:
                session.execute(
                    text(
                        "INSERT INTO memu_embedding_space (id, identity) VALUES (1, :identity) "
                        "ON CONFLICT(id) DO UPDATE SET identity = excluded.identity"
                    ),
                    {"identity": embedding_space},
                )
                session.commit()
        self._state.expected_embedding_space = embedding_space
        if initialize:
            self._state.embedding_space = embedding_space

    def replace_all_embeddings(
        self,
        *,
        resources: Mapping[str, list[float]],
        recall_files: Mapping[str, list[float]],
        segments: Mapping[str, list[float]],
        embedding_space: str,
    ) -> None:
        mappings = (
            (self._sqla_models.Resource, resources, self._sqla_models.Resource.caption.is_not(None)),
            (self._sqla_models.RecallFile, recall_files, None),
            (self._sqla_models.RecallFileSegment, segments, None),
        )
        with self._sessions.session() as session:
            session.execute(text("SELECT identity FROM memu_embedding_space WHERE id = 1 FOR UPDATE"))
            for model, vectors, predicate in mappings:
                stmt = select(model.id)
                if predicate is not None:
                    stmt = stmt.where(predicate)
                if set(session.execute(stmt).scalars()) != set(vectors):
                    raise KeyError(_REINDEX_CONFLICT)
                for item_id, vector in vectors.items():
                    result = cast(
                        Any, session.execute(update(model).where(model.id == item_id).values(embedding=list(vector)))
                    )
                    if result.rowcount != 1:
                        raise KeyError(_REINDEX_CONFLICT)
            session.execute(
                update(self._sqla_models.Resource)
                .where(self._sqla_models.Resource.caption.is_(None))
                .values(embedding=None)
            )
            session.execute(
                text(
                    "INSERT INTO memu_embedding_space (id, identity) VALUES (1, :identity) "
                    "ON CONFLICT(id) DO UPDATE SET identity = excluded.identity"
                ),
                {"identity": embedding_space},
            )
            session.commit()
        self._state.embedding_space = embedding_space
        self._state.expected_embedding_space = embedding_space
        self._load_existing()
