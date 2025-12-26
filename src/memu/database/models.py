from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

import pendulum
from pydantic import BaseModel, ConfigDict, Field

MemoryType = Literal["profile", "event", "knowledge", "behavior", "skill"]


class BaseRecord(BaseModel):
    """Backend-agnostic record interface."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: pendulum.now("UTC"))
    updated_at: datetime = Field(default_factory=lambda: pendulum.now("UTC"))


class Resource(BaseRecord):
    url: str
    modality: str
    local_path: str
    caption: str | None = None
    embedding: list[float] | None = None


class MemoryItem(BaseRecord):
    resource_id: str | None
    memory_type: MemoryType
    summary: str
    embedding: list[float] | None = None


class MemoryCategory(BaseRecord):
    name: str
    description: str
    embedding: list[float] | None = None
    summary: str | None = None


class CategoryItem(BaseRecord):
    item_id: str
    category_id: str


def merge_scope_model[TBaseRecord: BaseRecord](
    user_model: type[BaseModel], core_model: type[TBaseRecord], *, name_suffix: str
) -> type[TBaseRecord]:
    """Create a scoped model inheriting both the user scope model and the core model."""
    overlap = set(user_model.model_fields) & set(core_model.model_fields)
    if overlap:
        msg = f"Scope fields conflict with core model fields: {sorted(overlap)}"
        raise TypeError(msg)

    return type(
        f"{user_model.__name__}{core_model.__name__}{name_suffix}",
        (user_model, core_model),
        {"model_config": ConfigDict(extra="allow")},
    )


def build_scoped_models(
    user_model: type[BaseModel],
) -> tuple[type[Resource], type[MemoryCategory], type[MemoryItem], type[CategoryItem]]:
    """
    Build scoped interface models (Pydantic) that inherit from the base record models and user scope.
    """
    resource_model = merge_scope_model(user_model, Resource, name_suffix="Resource")
    memory_category_model = merge_scope_model(user_model, MemoryCategory, name_suffix="MemoryCategory")
    memory_item_model = merge_scope_model(user_model, MemoryItem, name_suffix="MemoryItem")
    category_item_model = merge_scope_model(user_model, CategoryItem, name_suffix="CategoryItem")
    return resource_model, memory_category_model, memory_item_model, category_item_model


__all__ = [
    "BaseRecord",
    "CategoryItem",
    "MemoryCategory",
    "MemoryItem",
    "MemoryType",
    "Resource",
    "build_scoped_models",
    "merge_scope_model",
]
