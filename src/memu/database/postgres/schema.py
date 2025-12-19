from __future__ import annotations

import time
from dataclasses import dataclass

try:  # Optional dependency - only required for Postgres backend
    from sqlmodel import Field, SQLModel
except ImportError as exc:  # pragma: no cover - optional dependency
    SQLModel = None
    Field = None
    _sqlmodel_import_error = exc
else:
    _sqlmodel_import_error = None

try:  # Optional dependency - only required for Postgres backend
    from sqlalchemy import Column, Float, ForeignKey, Index, MetaData, String, Text
    from sqlalchemy.dialects.postgresql import ARRAY
    from sqlalchemy.sql import func
except ImportError as exc:  # pragma: no cover - optional dependency
    Column = None
    Float = None
    ForeignKey = None
    Index = None
    MetaData = None
    String = None
    Text = None
    func = None
    ARRAY = None
    _sqlalchemy_import_error = exc
else:
    _sqlalchemy_import_error = None

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None


@dataclass
class SQLAModels:
    Base: type[SQLModel]
    Resource: type[SQLModel]
    MemoryCategory: type[SQLModel]
    MemoryItem: type[SQLModel]
    CategoryItem: type[SQLModel]


_MODEL_CACHE: dict[bool, SQLAModels] = {}


def require_sqlalchemy() -> None:
    if SQLModel is None or Column is None:
        msg = "sqlmodel (and sqlalchemy) is required for Postgres storage support"
        raise ImportError(msg) from (_sqlmodel_import_error or _sqlalchemy_import_error)


def _embedding_type(use_vector: bool):
    if use_vector:
        if Vector is None:
            msg = "pgvector is required when vector_provider='pgvector'"
            raise ImportError(msg)
        return Vector()
    return ARRAY(Float)


def get_sqlalchemy_models(use_vector: bool) -> SQLAModels:
    """
    Build (and cache) SQLModel ORM models for Postgres storage.
    use_vector toggles pgvector vs plain float array embedding storage.
    """
    require_sqlalchemy()
    cached = _MODEL_CACHE.get(use_vector)
    if cached:
        return cached

    embedding_col_type = _embedding_type(use_vector)
    metadata_obj = MetaData()

    class Base(SQLModel):
        __abstract__ = True
        metadata = metadata_obj

    class Resource(Base, table=True):
        __tablename__ = "resources"

        id: str | None = Field(default=None, primary_key=True, sa_column=Column(String, primary_key=True))
        scope_key: str = Field(sa_column=Column(String, nullable=False, index=True))
        url: str = Field(sa_column=Column(String, nullable=False))
        modality: str = Field(sa_column=Column(String, nullable=False))
        local_path: str = Field(sa_column=Column(String, nullable=False))
        caption: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
        embedding: list[float] | None = Field(default=None, sa_column=Column(embedding_col_type, nullable=True))
        created_at: float = Field(default_factory=time.time, sa_column=Column(Float, nullable=False))
        updated_at: float = Field(default_factory=time.time, sa_column=Column(Float, nullable=False))

    class MemoryCategory(Base, table=True):
        __tablename__ = "memory_categories"

        id: str | None = Field(default=None, primary_key=True, sa_column=Column(String, primary_key=True))
        scope_key: str = Field(sa_column=Column(String, nullable=False, index=True))
        name: str = Field(sa_column=Column(String, nullable=False))
        description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
        embedding: list[float] | None = Field(default=None, sa_column=Column(embedding_col_type, nullable=True))
        summary: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
        created_at: float = Field(default_factory=time.time, sa_column=Column(Float, nullable=False))
        updated_at: float = Field(default_factory=time.time, sa_column=Column(Float, nullable=False))

        __table_args__ = (Index("idx_categories_scope_name", "scope_key", func.lower(name), unique=True),)

    class MemoryItem(Base, table=True):
        __tablename__ = "memory_items"

        id: str | None = Field(default=None, primary_key=True, sa_column=Column(String, primary_key=True))
        scope_key: str = Field(sa_column=Column(String, nullable=False, index=True))
        resource_id: str = Field(sa_column=Column(ForeignKey("resources.id", ondelete="CASCADE"), nullable=False))
        memory_type: str = Field(sa_column=Column(String, nullable=False))
        summary: str = Field(sa_column=Column(Text, nullable=False))
        embedding: list[float] | None = Field(default=None, sa_column=Column(embedding_col_type, nullable=True))
        created_at: float = Field(default_factory=time.time, sa_column=Column(Float, nullable=False))
        updated_at: float = Field(default_factory=time.time, sa_column=Column(Float, nullable=False))

    class CategoryItem(Base, table=True):
        __tablename__ = "category_items"

        id: str | None = Field(default=None, primary_key=True, sa_column=Column(String, primary_key=True))
        scope_key: str = Field(sa_column=Column(String, nullable=False, index=True))
        item_id: str = Field(sa_column=Column(ForeignKey("memory_items.id", ondelete="CASCADE"), nullable=False))
        category_id: str = Field(
            sa_column=Column(ForeignKey("memory_categories.id", ondelete="CASCADE"), nullable=False)
        )
        created_at: float = Field(default_factory=time.time, sa_column=Column(Float, nullable=False))
        updated_at: float = Field(default_factory=time.time, sa_column=Column(Float, nullable=False))

        __table_args__ = (Index("idx_category_items_unique", "scope_key", "item_id", "category_id", unique=True),)

    models = SQLAModels(
        Base=Base,
        Resource=Resource,
        MemoryCategory=MemoryCategory,
        MemoryItem=MemoryItem,
        CategoryItem=CategoryItem,
    )
    _MODEL_CACHE[use_vector] = models
    return models


def get_metadata(use_vector: bool):
    return get_sqlalchemy_models(use_vector).Base.metadata


__all__ = ["SQLAModels", "Vector", "get_metadata", "get_sqlalchemy_models", "require_sqlalchemy"]
