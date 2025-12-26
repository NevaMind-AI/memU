from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any, override

from memu.database.inmemory.repositories.filter import matches_where
from memu.database.inmemory.state import InMemoryState
from memu.database.models import CategoryItem
from memu.database.repositories.category_item import CategoryItemRepo


class InMemoryCategoryItemRepository(CategoryItemRepo):
    def __init__(self, *, state: InMemoryState, category_item_model: type[CategoryItem]) -> None:
        self._state = state
        self.category_item_model = category_item_model
        self.relations: list[CategoryItem] = self._state.relations

    def list_relations(self, where: Mapping[str, Any] | None = None) -> list[CategoryItem]:
        if not where:
            return list(self.relations)
        return [rel for rel in self.relations if matches_where(rel, where)]

    def link_item_category(self, item_id: str, cat_id: str, user_data: dict[str, Any]) -> CategoryItem:
        _ = item_id  # enforced by caller via existing state
        for rel in self.relations:
            if rel.item_id == item_id and rel.category_id == cat_id:
                return rel
        rel = self.category_item_model(id=str(uuid.uuid4()), item_id=item_id, category_id=cat_id, **user_data)
        self.relations.append(rel)
        return rel

    def load_existing(self) -> None:
        return None

    @override
    def get_item_categories(self, item_id: str) -> list[CategoryItem]:
        return [rel for rel in self.relations if rel.item_id == item_id]

    @override
    def unlink_item_category(self, item_id: str, cat_id: str) -> None:
        self.relations = [rel for rel in self.relations if not (rel.item_id == item_id and rel.category_id == cat_id)]


__all__ = ["InMemoryCategoryItemRepository"]
