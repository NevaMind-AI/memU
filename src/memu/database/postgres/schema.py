from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

try:
    from sqlmodel import SQLModel
except ImportError as exc:
    msg = "sqlmodel is required for Postgres storage support"
    raise ImportError(msg) from exc

try:
    from sqlalchemy import MetaData
except ImportError as exc:
    msg = "sqlalchemy is required for Postgres storage support"
    raise ImportError(msg) from exc

try:
    from pgvector.sqlalchemy import VECTOR as Vector
except ImportError as exc:
    msg = "pgvector is required for Postgres vector support"
    raise ImportError(msg) from exc

from memu.database.postgres.models import (
    CategoryItemModel,
    MemoryCategoryModel,
    MemoryItemModel,
    ResourceModel,
    build_table_model,
)


@dataclass
class SQLAModels:
    Base: type[Any]
    Resource: type[Any]
    MemoryCategory: type[Any]
    MemoryItem: type[Any]
    CategoryItem: type[Any]


_MODEL_CACHE: dict[type[Any], SQLAModels] = {}


def require_sqlalchemy() -> None:
    return None


def get_sqlalchemy_models(*, scope_model: type[BaseModel] | None = None) -> SQLAModels:
    """
    Build (and cache) SQLModel ORM models for Postgres storage.
    """
    require_sqlalchemy()
    scope = scope_model or BaseModel
    cache_key = scope
    cached = _MODEL_CACHE.get(cache_key)
    if cached:
        return cached

    metadata_obj = MetaData()

    resource_model = build_table_model(
        scope,
        ResourceModel,
        tablename="resources",
        metadata=metadata_obj,
    )
    memory_category_model = build_table_model(
        scope,
        MemoryCategoryModel,
        tablename="memory_categories",
        metadata=metadata_obj,
    )
    memory_item_model = build_table_model(
        scope,
        MemoryItemModel,
        tablename="memory_items",
        metadata=metadata_obj,
    )
    category_item_model = build_table_model(
        scope,
        CategoryItemModel,
        tablename="category_items",
        metadata=metadata_obj,
    )

    class Base(SQLModel):
        __abstract__ = True
        metadata = metadata_obj

    models = SQLAModels(
        Base=Base,
        Resource=resource_model,
        MemoryCategory=memory_category_model,
        MemoryItem=memory_item_model,
        CategoryItem=category_item_model,
    )
    _MODEL_CACHE[cache_key] = models
    return models


def get_metadata(scope_model: type[BaseModel] | None = None) -> MetaData:
    from typing import cast

    return cast(MetaData, get_sqlalchemy_models(scope_model=scope_model).Base.metadata)


__all__ = ["SQLAModels", "Vector", "get_metadata", "get_sqlalchemy_models", "require_sqlalchemy"]
