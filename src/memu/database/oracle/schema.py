from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy import JSON, Column, String
from sqlmodel import Field

# We need the base Pydantic models from `memu.database.models`
from memu.database.models import (
    CategoryItem as CategoryItemModel,
)
from memu.database.models import (
    MemoryCategory as MemoryCategoryModel,
)
from memu.database.models import (
    MemoryItem as MemoryItemModel,
)
from memu.database.models import (
    Resource as ResourceModel,
)

try:
    from sqlmodel import SQLModel
except ImportError as exc:
    msg = "sqlmodel is required for Oracle storage support"
    raise ImportError(msg) from exc

try:
    from sqlalchemy import MetaData
except ImportError as exc:
    msg = "sqlalchemy is required for Oracle storage support"
    raise ImportError(msg) from exc

# Schema definitions needed for Oracle
# Defined locally to avoid dependencies on pgvector or other postgres-specific modules.


def build_table_model(
    scope_model: type[BaseModel],
    base_model: type[Any],
    *,
    tablename: str,
    metadata_obj: MetaData,
) -> type[Any]:
    """
    Dynamically create a SQLModel class that inherits from both scope_model and base_model.
    Replaces vector embeddings with JSON columns for Oracle compatibility.
    """

    # Create mixin with table args
    class TableMixin(SQLModel):
        __tablename__ = tablename
        metadata = metadata_obj

        id: str = Field(primary_key=True)

        # Override embedding field to use JSON
        if "embedding" in base_model.model_fields:
            embedding: list[float] | None = Field(default=None, sa_column=Column(JSON))

        # Override memory_type to use String (handles Literal issue)
        if "memory_type" in base_model.model_fields:
            memory_type: str = Field(sa_column=Column(String))

    # Combine classes
    metaclass = type(TableMixin)
    if scope_model is BaseModel:
        # No scope
        combined = metaclass(
            f"Oracle{base_model.__name__}",
            (TableMixin, base_model),
            {},
            table=True,
        )
    else:
        combined = metaclass(
            f"Oracle{base_model.__name__}",
            (TableMixin, scope_model, base_model),
            {},
            table=True,
        )

    return combined


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
    Build (and cache) SQLModel ORM models for Oracle storage.
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
        metadata_obj=metadata_obj,
    )
    memory_category_model = build_table_model(
        scope,
        MemoryCategoryModel,
        tablename="memory_categories",
        metadata_obj=metadata_obj,
    )
    memory_item_model = build_table_model(
        scope,
        MemoryItemModel,
        tablename="memory_items",
        metadata_obj=metadata_obj,
    )
    category_item_model = build_table_model(
        scope,
        CategoryItemModel,
        tablename="category_items",
        metadata_obj=metadata_obj,
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


__all__ = ["SQLAModels", "get_metadata", "get_sqlalchemy_models", "require_sqlalchemy"]
