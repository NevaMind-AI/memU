from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from pydantic import BaseModel

from memu.app.agentic import AgenticMixin
from memu.app.client_pool import ClientPool
from memu.app.settings import (
    DatabaseConfig,
    EmbeddingConfig,
    EmbeddingProfilesConfig,
    ProgressiveRetrieveConfig,
    UserConfig,
)
from memu.database.factory import build_database
from memu.database.interfaces import Database
from memu.embedding.gateway import build_embedding_client

TConfigModel = TypeVar("TConfigModel", bound=BaseModel)


class MemoryService(AgenticMixin):
    """Embedding-only memory service.

    Exposes the agentic surface — :meth:`~AgenticMixin.list_all_recall_files`,
    :meth:`~AgenticMixin.progressive_retrieve`, and
    :meth:`~AgenticMixin.commit_results` — over a pluggable store. No LLM is
    involved anywhere: the only model calls are embeddings for indexing and
    vector search.
    """

    def __init__(
        self,
        *,
        database_config: DatabaseConfig | dict[str, Any] | None = None,
        embedding_profiles: EmbeddingProfilesConfig | dict[str, Any] | None = None,
        progressive_retrieve_config: ProgressiveRetrieveConfig | dict[str, Any] | None = None,
        user_config: UserConfig | dict[str, Any] | None = None,
    ):
        self.user_config = self._validate_config(user_config, UserConfig)
        self.user_model = self.user_config.model
        self.database_config = self._validate_config(database_config, DatabaseConfig)
        self.progressive_retrieve_config = self._validate_config(progressive_retrieve_config, ProgressiveRetrieveConfig)
        self.embedding_profiles: dict[str, EmbeddingConfig] = self._validate_config(
            embedding_profiles, EmbeddingProfilesConfig
        ).profiles

        self.database: Database = build_database(
            config=self.database_config,
            user_model=self.user_model,
        )
        self._embedding_pool: ClientPool[EmbeddingConfig, Any] = ClientPool(
            profiles=self.embedding_profiles, builder=build_embedding_client, label="embedding"
        )

    def _get_database(self) -> Database:
        return self.database

    def _get_embedding_client(self, profile: str | None = None) -> Any:
        return self._embedding_pool.get(profile)

    def _normalize_where(self, where: Mapping[str, Any] | None) -> dict[str, Any]:
        """Validate and clean the `where` scope filters against the configured user model."""
        if not where:
            return {}

        valid_fields = set(getattr(self.user_model, "model_fields", {}).keys())
        cleaned: dict[str, Any] = {}

        for raw_key, value in where.items():
            if value is None:
                continue
            field = raw_key.split("__", 1)[0]
            if field not in valid_fields:
                msg = f"Unknown filter field '{field}' for current user scope"
                raise ValueError(msg)
            cleaned[raw_key] = value

        return cleaned

    def _model_dump_without_embeddings(self, obj: BaseModel) -> dict[str, Any]:
        return obj.model_dump(exclude={"embedding"})

    @staticmethod
    def _validate_config(
        config: Mapping[str, Any] | BaseModel | None,
        model_type: type[TConfigModel],
    ) -> TConfigModel:
        if isinstance(config, model_type):
            return config
        if config is None:
            return model_type()
        return model_type.model_validate(config)
