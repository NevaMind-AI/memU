"""SQLAlchemy schema definitions for SQLite backend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy import MetaData
from sqlmodel import SQLModel

from memu.database.sqlite.models import (
    SQLiteEntryModel,
    SQLiteResourceEntryModel,
    SQLiteResourceModel,
    build_sqlite_table_model,
)


@dataclass
class SQLiteSQLAModels:
    """Container for SQLite SQLAlchemy/SQLModel models."""

    Base: type[Any]
    Resource: type[Any]
    Entry: type[Any]
    ResourceEntry: type[Any]


_MODEL_CACHE: dict[type[Any], SQLiteSQLAModels] = {}


def get_sqlite_sqlalchemy_models(*, scope_model: type[BaseModel] | None = None) -> SQLiteSQLAModels:
    """Build (and cache) SQLModel ORM models for SQLite storage.

    Args:
        scope_model: Optional Pydantic model defining user scope fields.

    Returns:
        SQLiteSQLAModels containing all table models.
    """
    scope = scope_model or BaseModel
    cache_key = scope
    cached = _MODEL_CACHE.get(cache_key)
    if cached:
        return cached

    metadata_obj = MetaData()

    # NOTE: SQLite reserves any table name beginning with "sqlite_", so the tables
    # must use a different prefix.
    resource_model = build_sqlite_table_model(
        scope,
        SQLiteResourceModel,
        tablename="memu_resources",
        metadata=metadata_obj,
    )
    entry_model = build_sqlite_table_model(
        scope,
        SQLiteEntryModel,
        tablename="memu_entries",
        metadata=metadata_obj,
    )
    resource_entry_model = build_sqlite_table_model(
        scope,
        SQLiteResourceEntryModel,
        tablename="memu_resource_entries",
        metadata=metadata_obj,
        unique_with_scope=["entry_id", "resource_id"],
    )

    class SQLiteBase(SQLModel):
        __abstract__ = True
        metadata = metadata_obj

    models = SQLiteSQLAModels(
        Base=SQLiteBase,
        Resource=resource_model,
        Entry=entry_model,
        ResourceEntry=resource_entry_model,
    )
    _MODEL_CACHE[cache_key] = models
    return models


def get_sqlite_metadata(scope_model: type[BaseModel] | None = None) -> MetaData:
    """Get SQLAlchemy metadata for SQLite tables.

    Args:
        scope_model: Optional Pydantic model defining user scope fields.

    Returns:
        SQLAlchemy MetaData object.
    """
    from typing import cast

    return cast(MetaData, get_sqlite_sqlalchemy_models(scope_model=scope_model).Base.metadata)


__all__ = ["SQLiteSQLAModels", "get_sqlite_metadata", "get_sqlite_sqlalchemy_models"]
