from __future__ import annotations

from pydantic import BaseModel

from memu.app.settings import DatabaseConfig
from memu.database.postgres.postgres import PostgresStore
from memu.database.postgres.schema import SQLAModels, get_sqlalchemy_models


def build_postgres_database(
    *,
    config: DatabaseConfig,
    user_model: type[BaseModel],
) -> PostgresStore:
    dsn = config.metadata_store.dsn
    if not dsn:
        msg = "Postgres metadata_store requires a DSN"
        raise ValueError(msg)

    vector_provider = config.vector_index.provider if config.vector_index else None
    sqla_models: SQLAModels = get_sqlalchemy_models(scope_model=user_model)

    return PostgresStore(
        dsn=dsn,
        ddl_mode=config.metadata_store.ddl_mode,
        vector_provider=vector_provider,
        scope_model=user_model,
        resource_model=sqla_models.Resource,
        memory_category_model=sqla_models.MemoryCategory,
        memory_item_model=sqla_models.MemoryItem,
        category_item_model=sqla_models.CategoryItem,
        sqla_models=sqla_models,
    )


__all__ = ["build_postgres_database"]
