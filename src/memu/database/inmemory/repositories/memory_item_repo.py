from __future__ import annotations

import uuid

from memu.database.inmemory.state import InMemoryState
from memu.database.inmemory.vector import cosine_topk
from memu.database.models import MemoryItem, MemoryType
from memu.database.repositories.memory_item import MemoryItemRepo as MemoryItemRepoProtocol


class InMemoryMemoryItemRepository(MemoryItemRepoProtocol):
    def __init__(self, *, state: InMemoryState, memory_item_model: type[MemoryItem]) -> None:
        self._state = state
        self.memory_item_model = memory_item_model
        self.items: dict[str, MemoryItem] = self._state.items

    def create_item(
        self, *, resource_id: str, memory_type: MemoryType, summary: str, embedding: list[float]
    ) -> MemoryItem:
        mid = str(uuid.uuid4())
        it = self.memory_item_model(
            id=mid,
            resource_id=resource_id,
            memory_type=memory_type,
            summary=summary,
            embedding=embedding,
        )
        self.items[mid] = it
        return it

    def vector_search_items(self, query_vec: list[float], top_k: int) -> list[tuple[str, float]]:
        hits = cosine_topk(query_vec, [(i.id, i.embedding) for i in self.items.values()], k=top_k)
        return hits

    def load_existing(self) -> None:
        return None


MemoryItemRepo = InMemoryMemoryItemRepository

__all__ = ["InMemoryMemoryItemRepository", "MemoryItemRepo"]
