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

    def _find_by_hash(self, content_hash: str, user_data: dict[str, Any]) -> MemoryItem | None:
        """
        Find existing item by content hash within the same user scope.

        This enables deduplication: if the same content exists for the same user,
        we reinforce it instead of creating a duplicate.
        """
        for item in self.items.values():
            # Read content_hash from extra dict
            item_hash = (item.extra or {}).get("content_hash")
            if item_hash != content_hash:
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
        reinforce: bool = False,
        tool_record: dict[str, Any] | None = None,
    ) -> MemoryItem:
        if reinforce and memory_type != "tool":
            return self.create_item_reinforce(
                resource_id=resource_id,
                memory_type=memory_type,
                summary=summary,
                embedding=embedding,
                user_data=user_data,
            )

        # Build extra dict with tool_record fields at top level
        extra: dict[str, Any] = {}
        if tool_record:
            if tool_record.get("when_to_use") is not None:
                extra["when_to_use"] = tool_record["when_to_use"]
            if tool_record.get("metadata") is not None:
                extra["metadata"] = tool_record["metadata"]
            if tool_record.get("tool_calls") is not None:
                extra["tool_calls"] = tool_record["tool_calls"]

        mid = str(uuid.uuid4())
        it = self.memory_item_model(
            id=mid,
            resource_id=resource_id,
            memory_type=memory_type,
            summary=summary,
            embedding=embedding,
            extra=extra if extra else {},
            **user_data,
        )
        self.items[mid] = it
        return it

    def create_item_reinforce(
        self,
        *,
        resource_id: str,
        memory_type: MemoryType,
        summary: str,
        embedding: list[float],
        user_data: dict[str, Any],
        reinforce: bool = False,
    ) -> MemoryItem:
        content_hash = compute_content_hash(summary, memory_type)

        # Check for existing item with same hash in same scope (deduplication)
        existing = self._find_by_hash(content_hash, user_data)
        if existing:
            # Reinforce existing memory instead of creating duplicate
            current_extra = existing.extra or {}
            current_count = current_extra.get("reinforcement_count", 1)
            existing.extra = {
                **current_extra,
                "reinforcement_count": current_count + 1,
                "last_reinforced_at": pendulum.now("UTC").isoformat(),
            }
            existing.updated_at = pendulum.now("UTC")
            return existing

        # Create new item with salience tracking in extra
        mid = str(uuid.uuid4())
        now = pendulum.now("UTC")
        item_extra = user_data.pop("extra", {}) if "extra" in user_data else {}
        item_extra.update({
            "content_hash": content_hash,
            "reinforcement_count": 1,
            "last_reinforced_at": now.isoformat(),
        })
        it = self.memory_item_model(
            id=mid,
            resource_id=resource_id,
            memory_type=memory_type,
            summary=summary,
            embedding=embedding,
            extra=item_extra,
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
            # Read values from extra dict
            corpus = [
                (
                    i.id,
                    i.embedding,
                    (i.extra or {}).get("reinforcement_count", 1),
                    self._parse_datetime((i.extra or {}).get("last_reinforced_at")),
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

    @staticmethod
    def _parse_datetime(dt_str: str | None) -> pendulum.DateTime | None:
        """Parse ISO datetime string from extra dict."""
        if dt_str is None:
            return None
        try:
            parsed = pendulum.parse(dt_str)
        except (ValueError, TypeError):
            return None
        else:
            if isinstance(parsed, pendulum.DateTime):
                return parsed
            return None

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
        tool_record: dict[str, Any] | None = None,
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

        # Merge extra and tool_record into existing extra dict
        current_extra = item.extra or {}
        if extra is not None:
            current_extra = {**current_extra, **extra}
        if tool_record is not None:
            # Merge tool_record fields at top level
            for key in ("when_to_use", "metadata", "tool_calls"):
                if tool_record.get(key) is not None:
                    current_extra[key] = tool_record[key]
        if extra is not None or tool_record is not None:
            item.extra = current_extra

        self.items[item_id] = item
        return item


__all__ = ["InMemoryMemoryItemRepository"]
