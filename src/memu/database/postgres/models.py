from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import pendulum
from pydantic import BaseModel, create_model
from sqlalchemy import ForeignKey, MetaData, String, Text
from sqlmodel import Column, DateTime, Field, Index, SQLModel, func

from memu.database.models import CategoryItem, MemoryCategory, MemoryItem, MemoryType, Resource


class BaseModelMixin(SQLModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    created_at: datetime = Field(
        default_factory=lambda: pendulum.now("UTC"),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: pendulum.now("UTC"),
        sa_column=Column(DateTime(timezone=True)),
    )


class ResourceModel(Resource, BaseModelMixin):
    url: str = Field(sa_column=Column(String, nullable=False))
    modality: str = Field(sa_column=Column(String, nullable=False))
    local_path: str = Field(sa_column=Column(String, nullable=False))
    caption: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    embedding: list[float] | None = Field(default=None)


class MemoryItemModel(MemoryItem, BaseModelMixin):
    resource_id: str = Field(sa_column=Column(ForeignKey("resources.id", ondelete="CASCADE"), nullable=False))
    memory_type: MemoryType = Field(sa_column=Column(String, nullable=False))
    summary: str = Field(sa_column=Column(Text, nullable=False))
    embedding: list[float] | None = Field(default=None)


class MemoryCategoryModel(MemoryCategory, BaseModelMixin):
    name: str = Field(sa_column=Column(String, nullable=False))
    description: str = Field(sa_column=Column(Text, nullable=False))
    embedding: list[float] | None = Field(default=None)
    summary: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    __table_args__ = (Index("idx_categories_name", func.lower(name), unique=True),)


class CategoryItemModel(CategoryItem, BaseModelMixin):
    item_id: str = Field(sa_column=Column(ForeignKey("memory_items.id", ondelete="CASCADE"), nullable=False))
    category_id: str = Field(sa_column=Column(ForeignKey("memory_categories.id", ondelete="CASCADE"), nullable=False))

    __table_args__ = (Index("idx_category_items_unique", "item_id", "category_id", unique=True),)


def build_domain_model(user_model: type[BaseModel]) -> type[SQLModel]:
    fields = {}
    for name, finfo in user_model.model_fields.items():
        ann = finfo.annotation
        nullable = finfo.default_factory is not None
        kwargs: dict[str, Any] = {"index": True, "nullable": nullable}

        if finfo.default_factory is not None:
            kwargs["default_factory"] = finfo.default_factory

        fields[name] = (ann, Field(**kwargs))

    return create_model(f"{user_model.__name__}Scope", __base__=SQLModel, field_definitions=fields)


def _normalize_table_args(table_args: Any) -> tuple[list[Any], dict[str, Any]]:
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
    user_mixin = build_domain_model(user_model)
    overlap = set(user_mixin.model_fields) & set(core_model.model_fields)
    if overlap:
        msg = f"Scope fields conflict with core model fields: {sorted(overlap)}"
        raise TypeError(msg)

    return type(
        f"{user_model.__name__}{core_model.__name__}{name_suffix}",
        (user_mixin, core_model),
        base_attrs,
    )


def build_table_model(
    user_model: type[BaseModel],
    core_model: type[SQLModel],
    *,
    tablename: str,
    metadata: MetaData | None = None,
    extra_table_args: tuple[Any, ...] | None = None,
) -> type[SQLModel]:
    user_mixin = build_domain_model(user_model)
    overlap = set(user_mixin.model_fields) & set(core_model.model_fields)
    if overlap:
        msg = f"Scope fields conflict with core model fields: {sorted(overlap)}"
        raise TypeError(msg)

    scope_fields = list(user_mixin.model_fields.keys())
    base_table_args, table_kwargs = _normalize_table_args(getattr(core_model, "__table_args__", None))
    table_args = list(base_table_args)
    if extra_table_args:
        table_args.extend(extra_table_args)
    if scope_fields:
        table_args.append(Index(f"ix_{tablename}__scope", *scope_fields))

    base_attrs: dict[str, Any] = {"__module__": core_model.__module__, "__tablename__": tablename}
    if metadata is not None:
        base_attrs["metadata"] = metadata
    if table_args or table_kwargs:
        if table_kwargs:
            base_attrs["__table_args__"] = (*table_args, table_kwargs)
        else:
            base_attrs["__table_args__"] = tuple(table_args)

    base = _merge_models(user_model, core_model, name_suffix="Base", base_attrs=base_attrs)

    return create_model(
        f"{user_model.__name__}{core_model.__name__}Table",
        __base__=base,
        __module__=core_model.__module__,
        __cls_kwargs__={"table": True},
    )


def build_scoped_models(
    user_model: type[BaseModel],
) -> tuple[type[SQLModel], type[SQLModel], type[SQLModel], type[SQLModel]]:
    """
    Build scoped SQLModel tables for each entity (resource, category, item, relation).
    """
    resource_model = build_table_model(user_model, ResourceModel, tablename="resources")
    memory_category_model = build_table_model(user_model, MemoryCategoryModel, tablename="memory_categories")
    memory_item_model = build_table_model(user_model, MemoryItemModel, tablename="memory_items")
    category_item_model = build_table_model(user_model, CategoryItemModel, tablename="category_items")
    return resource_model, memory_category_model, memory_item_model, category_item_model


__all__ = [
    "BaseModelMixin",
    "CategoryItemModel",
    "MemoryCategoryModel",
    "MemoryItemModel",
    "ResourceModel",
    "build_domain_model",
    "build_scoped_models",
    "build_table_model",
]
