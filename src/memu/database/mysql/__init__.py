from __future__ import annotations

from pydantic import BaseModel

from memu.app.settings import DatabaseConfig
from memu.database.mysql.mysql import MySQLStore
from memu.database.mysql.schema import SQLAModels, get_sqlalchemy_models


def build_mysql_database(
    *,
    config: DatabaseConfig,
    user_model: type[BaseModel],
) -> MySQLStore:
    dsn = config.metadata_store.dsn
    if not dsn:
        msg = "MySQL metadata_store requires a DSN"
        raise ValueError(msg)

    sqla_models: SQLAModels = get_sqlalchemy_models(scope_model=user_model)

    return MySQLStore(
        dsn=dsn,
        ddl_mode=config.metadata_store.ddl_mode,
        scope_model=user_model,
        resource_model=sqla_models.Resource,
        memory_category_model=sqla_models.MemoryCategory,
        memory_item_model=sqla_models.MemoryItem,
        category_item_model=sqla_models.CategoryItem,
        sqla_models=sqla_models,
    )


__all__ = ["build_mysql_database"]
