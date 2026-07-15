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

from memu.app.settings import DefaultUserModel
from memu.database.postgres.models import (
    RecallFileModel,
    RecallFileResourceModel,
    RecallFileSegmentModel,
    ResourceModel,
    build_table_model,
)

# Default user scope for the committed Alembic baseline. ``DefaultUserModel``
# (in ``memu.app.settings``) is the single source of truth for the built-in
# scope columns (``user_id`` / ``agent_id``); this alias keeps the schema and
# the migration generated against it in sync with the app default.
DefaultScope = DefaultUserModel


@dataclass
class SQLAModels:
    Base: type[Any]
    Resource: type[Any]
    RecallFile: type[Any]
    RecallFileResource: type[Any]
    RecallFileSegment: type[Any]


_MODEL_CACHE: dict[type[Any], SQLAModels] = {}


def require_sqlalchemy() -> None:
    return None


def get_sqlalchemy_models(*, scope_model: type[BaseModel] | None = None) -> SQLAModels:
    """
    Build (and cache) SQLModel ORM models for Postgres storage.
    """
    require_sqlalchemy()
    scope = scope_model or DefaultScope
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
    recall_file_model = build_table_model(
        scope,
        RecallFileModel,
        tablename="recall_files",
        metadata=metadata_obj,
    )
    recall_file_resource_model = build_table_model(
        scope,
        RecallFileResourceModel,
        tablename="recall_file_resources",
        metadata=metadata_obj,
    )
    recall_file_segment_model = build_table_model(
        scope,
        RecallFileSegmentModel,
        tablename="recall_file_segments",
        metadata=metadata_obj,
    )

    class Base(SQLModel):
        __abstract__ = True
        metadata = metadata_obj

    models = SQLAModels(
        Base=Base,
        Resource=resource_model,
        RecallFile=recall_file_model,
        RecallFileResource=recall_file_resource_model,
        RecallFileSegment=recall_file_segment_model,
    )
    _MODEL_CACHE[cache_key] = models
    return models


def get_metadata(scope_model: type[BaseModel] | None = None) -> MetaData:
    from typing import cast

    return cast(MetaData, get_sqlalchemy_models(scope_model=scope_model).Base.metadata)


__all__ = ["SQLAModels", "Vector", "get_metadata", "get_sqlalchemy_models", "require_sqlalchemy"]
