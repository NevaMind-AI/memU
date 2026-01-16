from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any, override

import pendulum

from memu.database.inmemory.repositories.filter import matches_where
from memu.database.inmemory.state import InMemoryState
from memu.database.inmemory.vector import cosine_topk, cosine_topk_salience
from memu.database.models import MemoryItem, MemoryType, compute_content_hash
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

    def _find_by_hash(self, content_hash: str, user_data: dict[str, Any]) -> MemoryItem | None:
        """
        Find existing item by content hash within the same user scope.

        This enables deduplication: if the same content exists for the same user,
        we reinforce it instead of creating a duplicate.
        """
        for item in self.items.values():
            if getattr(item, "content_hash", None) != content_hash:
                continue
            # Check scope match (user_id, agent_id, etc.)
            if matches_where(item, user_data):
                return item
        return None

    def create_item(
        self,
        *,
        resource_id: str,
        memory_type: MemoryType,
        summary: str,
        embedding: list[float],
        user_data: dict[str, Any],
    ) -> MemoryItem:
        content_hash = compute_content_hash(summary, memory_type)

        # Check for existing item with same hash in same scope (deduplication)
        existing = self._find_by_hash(content_hash, user_data)
        if existing:
            # Reinforce existing memory instead of creating duplicate
            existing.reinforcement_count = getattr(existing, "reinforcement_count", 1) + 1
            existing.last_reinforced_at = pendulum.now("UTC")
            existing.updated_at = pendulum.now("UTC")
            return existing

        # Create new item
        mid = str(uuid.uuid4())
        it = self.memory_item_model(
            id=mid,
            resource_id=resource_id,
            memory_type=memory_type,
            summary=summary,
            embedding=embedding,
            content_hash=content_hash,
            reinforcement_count=1,
            last_reinforced_at=pendulum.now("UTC"),
            **user_data,
        )
        self.items[mid] = it
        return it

    def vector_search_items(
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
        *,
        ranking: str = "similarity",
        recency_decay_days: float = 30.0,
    ) -> list[tuple[str, float]]:
        pool = self.list_items(where)

        if ranking == "salience":
            # Salience-aware ranking: similarity x reinforcement x recency
            corpus = [
                (
                    i.id,
                    i.embedding,
                    getattr(i, "reinforcement_count", 1),
                    getattr(i, "last_reinforced_at", None),
                )
                for i in pool.values()
            ]
            return cosine_topk_salience(query_vec, corpus, k=top_k, recency_decay_days=recency_decay_days)

        # Default: pure cosine similarity (backward compatible)
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

        self.items[item_id] = item
        return item


__all__ = ["InMemoryMemoryItemRepository"]
