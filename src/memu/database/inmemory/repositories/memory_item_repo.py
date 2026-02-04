from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any, override

from memu.database.inmemory.repositories.filter import matches_where
from memu.database.inmemory.state import InMemoryState
from memu.database.inmemory.vector import cosine_topk
from memu.database.models import MemoryItem, MemoryType
from memu.database.repositories.memory_item import MemoryItemRepo


class InMemoryMemoryItemRepository(MemoryItemRepo):
    def __init__(self, *, state: InMemoryState, memory_item_model: type[MemoryItem]) -> None:
        self._state = state
        self.memory_item_model = memory_item_model
        self.items: dict[str, MemoryItem] = self._state.items

    def list_items(self, where: Mapping[str, Any] | None = None) -> dict[str, MemoryItem]:
        if not where:
            return dict(self.items)
        return {mid: item for mid, item in self.items.items() if matches_where(item, where)}

    def list_items_by_ref_ids(
        self, ref_ids: list[str], where: Mapping[str, Any] | None = None
    ) -> dict[str, MemoryItem]:
        """List items by their ref_id in the extra column.

        Args:
            ref_ids: List of ref_ids to query.
            where: Additional filter conditions.

        Returns:
            Dict mapping item_id -> MemoryItem for items whose extra.ref_id is in ref_ids.
        """
        if not ref_ids:
            return {}
        ref_id_set = set(ref_ids)
        result: dict[str, MemoryItem] = {}
        for mid, item in self.items.items():
            # Check where filter first
            if where and not matches_where(item, where):
                continue
            # Check if ref_id is in the requested set
            item_ref_id = (item.extra or {}).get("ref_id")
            if item_ref_id and item_ref_id in ref_id_set:
                result[mid] = item
        return result

    def clear_items(self, where: Mapping[str, Any] | None = None) -> dict[str, MemoryItem]:
        if not where:
            matches = self.items.copy()
            self.items.clear()
            return matches
        matches = {mid: item for mid, item in self.items.items() if matches_where(item, where)}
        self.items = {mid: item for mid, item in self.items.items() if mid not in matches}
        return matches

    def create_item(
        self,
        *,
        resource_id: str,
        memory_type: MemoryType,
        summary: str,
        embedding: list[float],
        user_data: dict[str, Any],
    ) -> MemoryItem:
        mid = str(uuid.uuid4())
        it = self.memory_item_model(
            id=mid,
            resource_id=resource_id,
            memory_type=memory_type,
            summary=summary,
            embedding=embedding,
            **user_data,
        )
        self.items[mid] = it
        return it

    def vector_search_items(
        self, query_vec: list[float], top_k: int, where: Mapping[str, Any] | None = None
    ) -> list[tuple[str, float]]:
        pool = self.list_items(where)
        hits = cosine_topk(query_vec, [(i.id, i.embedding) for i in pool.values()], k=top_k)
        return hits

    def load_existing(self) -> None:
        return None

    def get_item(self, item_id: str) -> MemoryItem | None:
        return self.items.get(item_id)

    @override
    def delete_item(self, item_id: str) -> None:
        if item_id in self.items:
            del self.items[item_id]

    @override
    def update_item(
        self,
        *,
        item_id: str,
        memory_type: MemoryType | None = None,
        summary: str | None = None,
        embedding: list[float] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> MemoryItem:
        item = self.items.get(item_id)
        if item is None:
            msg = f"Item with id {item_id} not found"
            raise KeyError(msg)

        if memory_type is not None:
            item.memory_type = memory_type
        if summary is not None:
            item.summary = summary
        if embedding is not None:
            item.embedding = embedding
        if extra is not None:
            # Incremental update: merge new keys into existing extra dict
            current_extra = item.extra or {}
            merged_extra = {**current_extra, **extra}
            item.extra = merged_extra

        self.items[item_id] = item
        return item


__all__ = ["InMemoryMemoryItemRepository"]
