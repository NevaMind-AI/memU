from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from memu.database.models import MemoryItem, MemoryType


@runtime_checkable
class MemoryItemRepo(Protocol):
    """Repository contract for memory items."""

    items: dict[str, MemoryItem]

    def get_item(self, item_id: str) -> MemoryItem | None: ...

    def list_items(self, where: Mapping[str, Any] | None = None) -> dict[str, MemoryItem]: ...

    def create_item(
        self,
        *,
        resource_id: str,
        memory_type: MemoryType,
        summary: str,
        embedding: list[float],
        user_data: dict[str, Any],
    ) -> MemoryItem: ...

    def update_item(
        self,
        *,
        item_id: str,
        memory_type: MemoryType | None = None,
        summary: str | None = None,
        embedding: list[float] | None = None,
    ) -> MemoryItem: ...

    def delete_item(self, item_id: str) -> None: ...

    def vector_search_items(
        self, query_vec: list[float], top_k: int, where: Mapping[str, Any] | None = None
    ) -> list[tuple[str, float]]: ...

    def load_existing(self) -> None: ...
