"""SQLite-specific models for MemU database storage."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import pendulum
from pydantic import BaseModel
from sqlalchemy import JSON, MetaData, String, Text
from sqlmodel import Column, DateTime, Field, Index, SQLModel, func

from memu.database.models import Entry, Resource, ResourceEntry


class TZDateTime(DateTime):
    """DateTime type with timezone support."""

    def __init__(self, timezone: bool = True, **kw: Any) -> None:
        super().__init__(timezone=timezone, **kw)


class SQLiteBaseModelMixin(SQLModel):
    """Base mixin for SQLite models with common fields."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        sa_type=String,
    )
    created_at: datetime = Field(
        default_factory=lambda: pendulum.now("UTC"),
        sa_type=TZDateTime,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default_factory=lambda: pendulum.now("UTC"),
        sa_type=TZDateTime,
    )


class SQLiteResourceModel(SQLiteBaseModelMixin, Resource):
    """SQLite resource model.

    A single physical table holds both raw inputs (``lane="source"``) and the
    generated lane docs (``lane`` in {index, memory, skill}).
    """

    lane: str = Field(default="source", sa_column=Column(String, nullable=False, index=True))
    modality: str = Field(sa_column=Column(String, nullable=False))
    url: str | None = Field(default=None, sa_column=Column(String, nullable=True))
    local_path: str | None = Field(default=None, sa_column=Column(String, nullable=True))
    slug: str | None = Field(default=None, sa_column=Column(String, nullable=True))
    title: str | None = Field(default=None, sa_column=Column(String, nullable=True))
    description: str | None = Field(default=None, sa_column=Column(String, nullable=True))
    content: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    summary: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    # Override inherited embedding field: SQLite has no native vector type, so store the
    # vector in a JSON column (a bare ``list`` annotation is not mappable by SQLModel).
    embedding: list[float] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    resource_refs: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON, nullable=True))


class SQLiteEntryModel(SQLiteBaseModelMixin, Entry):
    """SQLite entry model (the searchable atoms of a lane)."""

    lane: str = Field(sa_column=Column(String, nullable=False, index=True))
    source_id: str | None = Field(default=None, sa_column=Column(String, nullable=True))
    source_path: str | None = Field(default=None, sa_column=Column(String, nullable=True))
    entry_kind: str = Field(sa_column=Column(String, nullable=False))
    text: str = Field(sa_column=Column(Text, nullable=False))
    # Override inherited embedding field: SQLite has no native vector type, so store the
    # vector in a JSON column (a bare ``list`` annotation is not mappable by SQLModel).
    embedding: list[float] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    happened_at: datetime | None = Field(default=None, sa_column=Column(DateTime, nullable=True))
    extra: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=True))


class SQLiteResourceEntryModel(SQLiteBaseModelMixin, ResourceEntry):
    """SQLite entry <-> coarse-resource membership edge model."""

    entry_id: str = Field(sa_column=Column(String, nullable=False))
    resource_id: str = Field(sa_column=Column(String, nullable=False))


def _normalize_table_args(table_args: Any) -> tuple[list[Any], dict[str, Any]]:
    """Normalize SQLAlchemy table args to a consistent format."""
    if table_args is None:
        return [], {}
    if isinstance(table_args, dict):
        return [], dict(table_args)
    if not isinstance(table_args, tuple):
        return [table_args], {}

    args = list(table_args)
    kwargs: dict[str, Any] = {}
    if args and isinstance(args[-1], dict):
        kwargs = dict(args.pop())
    return args, kwargs


def _merge_models(
    user_model: type[BaseModel],
    core_model: type[SQLModel],
    *,
    name_suffix: str,
    base_attrs: dict[str, Any],
) -> type[SQLModel]:
    """Merge user scope model with core SQLModel."""
    overlap = set(user_model.model_fields) & set(core_model.model_fields)
    if overlap:
        msg = f"Scope fields conflict with core model fields: {sorted(overlap)}"
        raise TypeError(msg)

    return type(
        f"{user_model.__name__}{core_model.__name__}{name_suffix}",
        (user_model, core_model),
        base_attrs,
    )


def build_sqlite_table_model(
    user_model: type[BaseModel],
    core_model: type[SQLModel],
    *,
    tablename: str,
    metadata: MetaData | None = None,
    extra_table_args: tuple[Any, ...] | None = None,
    unique_with_scope: list[str] | None = None,
) -> type[SQLModel]:
    """Build a scoped SQLite table model."""
    overlap = set(user_model.model_fields) & set(core_model.model_fields)
    if overlap:
        msg = f"Scope fields conflict with core model fields: {sorted(overlap)}"
        raise TypeError(msg)

    scope_fields = list(user_model.model_fields.keys())
    base_table_args, table_kwargs = _normalize_table_args(getattr(core_model, "__table_args__", None))
    table_args = list(base_table_args)
    if extra_table_args:
        table_args.extend(extra_table_args)
    if scope_fields:
        table_args.append(Index(f"ix_{tablename}__scope", *scope_fields))
    if unique_with_scope:
        unique_cols = [*unique_with_scope, *scope_fields]
        table_args.append(Index(f"ix_{tablename}__unique_scoped", *unique_cols, unique=True))

    base_attrs: dict[str, Any] = {"__module__": core_model.__module__, "__tablename__": tablename}
    if metadata is not None:
        base_attrs["metadata"] = metadata
    if table_args or table_kwargs:
        if table_kwargs:
            base_attrs["__table_args__"] = (*table_args, table_kwargs)
        else:
            base_attrs["__table_args__"] = tuple(table_args)

    base = _merge_models(user_model, core_model, name_suffix="SQLiteBase", base_attrs=base_attrs)

    # Use type() instead of create_model to properly preserve SQLModel table behavior
    table_attrs: dict[str, Any] = {"__module__": core_model.__module__}
    return type(
        f"{user_model.__name__}{core_model.__name__}SQLiteTable",
        (base,),
        table_attrs,
        table=True,
    )


__all__ = [
    "SQLiteBaseModelMixin",
    "SQLiteEntryModel",
    "SQLiteResourceEntryModel",
    "SQLiteResourceModel",
    "build_sqlite_table_model",
]
