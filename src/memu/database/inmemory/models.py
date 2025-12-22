from __future__ import annotations

from pydantic import BaseModel

from memu.database.models import (
    CategoryItem,
    MemoryCategory,
    MemoryItem,
    Resource,
    merge_scope_model,
)


class InMemoryResource(Resource):
    """Concrete in-memory resource model."""


class InMemoryMemoryItem(MemoryItem):
    """Concrete in-memory memory item model."""


class InMemoryMemoryCategory(MemoryCategory):
    """Concrete in-memory memory category model."""


class InMemoryCategoryItem(CategoryItem):
    """Concrete in-memory relation model."""


def build_inmemory_models(
    user_model: type[BaseModel],
) -> tuple[
    type[InMemoryResource],
    type[InMemoryMemoryCategory],
    type[InMemoryMemoryItem],
    type[InMemoryCategoryItem],
]:
    """
    Build scoped in-memory models that inherit from both the base interface and the user scope model.
    """
    resource_model = merge_scope_model(user_model, InMemoryResource, name_suffix="Resource")
    memory_category_model = merge_scope_model(user_model, InMemoryMemoryCategory, name_suffix="MemoryCategory")
    memory_item_model = merge_scope_model(user_model, InMemoryMemoryItem, name_suffix="MemoryItem")
    category_item_model = merge_scope_model(user_model, InMemoryCategoryItem, name_suffix="CategoryItem")
    return resource_model, memory_category_model, memory_item_model, category_item_model


__all__ = [
    "InMemoryCategoryItem",
    "InMemoryMemoryCategory",
    "InMemoryMemoryItem",
    "InMemoryResource",
    "build_inmemory_models",
]
