from __future__ import annotations

from typing import Protocol, runtime_checkable

from memu.database.models import MemoryItem, MemoryType


@runtime_checkable
class MemoryItemRepo(Protocol):
    """Repository contract for memory items."""

    items: dict[str, MemoryItem]

    def create_item(
        self, *, resource_id: str, memory_type: MemoryType, summary: str, embedding: list[float]
    ) -> MemoryItem: ...

    def vector_search_items(self, query_vec: list[float], top_k: int) -> list[tuple[str, float]]: ...

    def load_existing(self) -> None: ...
