from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from memu.app.settings import StorageProvidersConfig
from memu.database.inmemory.models import build_memory_models
from memu.database.inmemory.repo import InMemoryStore


@dataclass
class DatabaseLayer:
    base_model: type[BaseModel]
    resource_model: type[BaseModel]
    memory_item_model: type[BaseModel]
    memory_category_model: type[BaseModel]
    category_item_model: type[BaseModel]
    store_factory: Callable[[str], InMemoryStore]


def init_database_layer(
    *,
    user_model: type[BaseModel],
    storage_providers: StorageProvidersConfig,
) -> DatabaseLayer:
    """
    Build database-layer models and a store factory based on configured providers.

    The service delegates model creation and store selection here so that it only
    passes configuration objects and does not manage backend details.
    """
    (
        base_model_cls,
        resource_model,
        memory_item_model,
        memory_category_model,
        category_item_model,
    ) = build_memory_models(user_model)
    model_kwargs = {
        "base_model": base_model_cls,
        "resource_model": resource_model,
        "memory_item_model": memory_item_model,
        "memory_category_model": memory_category_model,
        "category_item_model": category_item_model,
    }

    provider = storage_providers.metadata_store.provider
    if provider == "postgres":
        dsn = storage_providers.metadata_store.dsn
        if not dsn:
            msg = "Postgres metadata_store requires a DSN"
            raise ValueError(msg)
        vector_provider = storage_providers.vector_index.provider if storage_providers.vector_index else None

        def store_factory(scope_key: str) -> InMemoryStore:
            from memu.database.postgres.postgres import PostgresStore

            return PostgresStore(
                dsn=dsn,
                scope_key=scope_key,
                ddl_mode=storage_providers.metadata_store.ddl_mode,
                vector_provider=vector_provider,
                **model_kwargs,
            )

        return DatabaseLayer(
            base_model=base_model_cls,
            resource_model=resource_model,
            memory_item_model=memory_item_model,
            memory_category_model=memory_category_model,
            category_item_model=category_item_model,
            store_factory=store_factory,
        )

    return DatabaseLayer(
        base_model=base_model_cls,
        resource_model=resource_model,
        memory_item_model=memory_item_model,
        memory_category_model=memory_category_model,
        category_item_model=category_item_model,
        store_factory=lambda scope_key: InMemoryStore(scope_key=scope_key, **model_kwargs),
    )
