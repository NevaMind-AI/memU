from __future__ import annotations

import uuid

from memu.database.inmemory.state import InMemoryState
from memu.database.models import CategoryItem
from memu.database.repositories.category_item import CategoryItemRepo as CategoryItemRepoProtocol


class InMemoryCategoryItemRepository(CategoryItemRepoProtocol):
    def __init__(self, *, state: InMemoryState, category_item_model: type[CategoryItem]) -> None:
        self._state = state
        self.category_item_model = category_item_model
        self.relations: list[CategoryItem] = self._state.relations

    def link_item_category(self, item_id: str, cat_id: str) -> CategoryItem:
        _ = item_id  # enforced by caller via existing state
        for rel in self.relations:
            if rel.item_id == item_id and rel.category_id == cat_id:
                return rel
        rel = self.category_item_model(id=str(uuid.uuid4()), item_id=item_id, category_id=cat_id)
        self.relations.append(rel)
        return rel

    def load_existing(self) -> None:
        return None


CategoryItemRepo = InMemoryCategoryItemRepository

__all__ = ["CategoryItemRepo", "InMemoryCategoryItemRepository"]
