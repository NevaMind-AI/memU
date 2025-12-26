from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from memu.database.inmemory.models import build_inmemory_models
from memu.database.inmemory.repositories import (
    InMemoryCategoryItemRepository,
    InMemoryMemoryCategoryRepository,
    InMemoryMemoryItemRepository,
    InMemoryResourceRepository,
)
from memu.database.inmemory.state import InMemoryState
from memu.database.interfaces import Database
from memu.database.models import CategoryItem, MemoryCategory, MemoryItem, Resource
from memu.database.repositories import MemoryCategoryRepo, ResourceRepo


class InMemoryStore(Database):
    def __init__(
        self,
        *,
        scope_model: type[BaseModel] | None = None,
        resource_model: type[Any] | None = None,
        memory_item_model: type[Any] | None = None,
        memory_category_model: type[Any] | None = None,
        category_item_model: type[Any] | None = None,
        state: InMemoryState | None = None,
    ) -> None:
        self.scope_model = scope_model or BaseModel
        (
            default_resource_model,
            default_memory_category_model,
            default_memory_item_model,
            default_category_item_model,
        ) = build_inmemory_models(self.scope_model)

        self.state = state or InMemoryState()
        self.resources: dict[str, Resource] = self.state.resources
        self.items: dict[str, MemoryItem] = self.state.items
        self.categories: dict[str, MemoryCategory] = self.state.categories
        self.relations: list[CategoryItem] = self.state.relations

        resource_model = resource_model or default_resource_model or Resource
        memory_item_model = memory_item_model or default_memory_item_model or MemoryItem
        memory_category_model = memory_category_model or default_memory_category_model or MemoryCategory
        category_item_model = category_item_model or default_category_item_model or CategoryItem

        self.resource_repo: ResourceRepo = InMemoryResourceRepository(state=self.state, resource_model=resource_model)
        self.memory_category_repo: MemoryCategoryRepo = InMemoryMemoryCategoryRepository(
            state=self.state, memory_category_model=memory_category_model
        )
        self.memory_item_repo = InMemoryMemoryItemRepository(state=self.state, memory_item_model=memory_item_model)
        self.category_item_repo = InMemoryCategoryItemRepository(
            state=self.state, category_item_model=category_item_model
        )

    def close(self) -> None:
        return None
