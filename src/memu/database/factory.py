from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel

from memu.app.settings import StorageProvidersConfig
from memu.database.inmemory.models import build_inmemory_models
from memu.database.inmemory.repo import InMemoryStore
from memu.database.interfaces import Database


def build_database_models(
    *,
    storage_providers: StorageProvidersConfig,
    user_model: type[BaseModel],
) -> dict[str, Any]:
    """Build backend-specific database models for the configured provider."""
    provider = storage_providers.metadata_store.provider
    if provider == "postgres":
        from memu.database.postgres.schema import SQLAModels, get_sqlalchemy_models

        sqla_models: SQLAModels = get_sqlalchemy_models(scope_model=user_model)
        return {
            "resource_model": sqla_models.Resource,
            "memory_category_model": sqla_models.MemoryCategory,
            "memory_item_model": sqla_models.MemoryItem,
            "category_item_model": sqla_models.CategoryItem,
            "sqla_models": sqla_models,
        }

    if provider == "inmemory":
        resource_model, memory_category_model, memory_item_model, category_item_model = build_inmemory_models(
            user_model
        )
        return {
            "resource_model": resource_model,
            "memory_category_model": memory_category_model,
            "memory_item_model": memory_item_model,
            "category_item_model": category_item_model,
        }

    msg = f"Unsupported metadata_store provider: {provider}"
    raise ValueError(msg)


def build_database(
    *,
    storage_providers: StorageProvidersConfig,
    user_model: type[BaseModel],
) -> Database:
    """
    Initialize a database backend for the configured provider.
    """
    provider = storage_providers.metadata_store.provider
    models: dict[str, Any] = build_database_models(storage_providers=storage_providers, user_model=user_model)
    if provider == "postgres":
        dsn = storage_providers.metadata_store.dsn
        if not dsn:
            msg = "Postgres metadata_store requires a DSN"
            raise ValueError(msg)
        vector_provider = storage_providers.vector_index.provider if storage_providers.vector_index else None

        from memu.database.postgres.postgres import PostgresStore
        from memu.database.postgres.schema import SQLAModels

        return PostgresStore(
            dsn=dsn,
            ddl_mode=storage_providers.metadata_store.ddl_mode,
            vector_provider=vector_provider,
            scope_model=user_model,
            resource_model=cast(type[Any], models["resource_model"]),
            memory_category_model=cast(type[Any], models["memory_category_model"]),
            memory_item_model=cast(type[Any], models["memory_item_model"]),
            category_item_model=cast(type[Any], models["category_item_model"]),
            sqla_models=cast(SQLAModels | None, models.get("sqla_models")),
        )

    if provider == "inmemory":
        return InMemoryStore(
            scope_model=user_model,
            resource_model=models["resource_model"],
            memory_item_model=models["memory_item_model"],
            memory_category_model=models["memory_category_model"],
            category_item_model=models["category_item_model"],
        )

    msg = f"Unsupported metadata_store provider: {provider}"
    raise ValueError(msg)
