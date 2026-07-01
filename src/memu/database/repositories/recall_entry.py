from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, Protocol, runtime_checkable

from memu.database.models import EntryType, RecallEntry


@runtime_checkable
class RecallEntryRepo(Protocol):
    """Repository contract for memory items."""

    items: dict[str, RecallEntry]

    def get_item(self, item_id: str) -> RecallEntry | None: ...

    def list_items(self, where: Mapping[str, Any] | None = None) -> dict[str, RecallEntry]: ...

    def clear_items(self, where: Mapping[str, Any] | None = None) -> dict[str, RecallEntry]: ...

    def create_item(
        self,
        *,
        resource_id: str,
        memory_type: EntryType,
        summary: str,
        embedding: list[float],
        user_data: dict[str, Any],
        reinforce: bool = False,
        tool_record: dict[str, Any] | None = None,
    ) -> RecallEntry: ...

    def update_item(
        self,
        *,
        item_id: str,
        memory_type: EntryType | None = None,
        summary: str | None = None,
        embedding: list[float] | None = None,
        extra: dict[str, Any] | None = None,
        tool_record: dict[str, Any] | None = None,
    ) -> RecallEntry: ...

    def delete_item(self, item_id: str) -> None: ...

    def list_items_by_ref_ids(
        self, ref_ids: list[str], where: Mapping[str, Any] | None = None
    ) -> dict[str, RecallEntry]: ...

    def vector_search_items(
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
        *,
        ranking: Literal["similarity", "salience"] = "similarity",
        recency_decay_days: float = 30.0,
    ) -> list[tuple[str, float]]: ...

    def load_existing(self) -> None: ...
