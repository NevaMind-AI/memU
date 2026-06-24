from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, Protocol, runtime_checkable

from memu.database.models import Entry


@runtime_checkable
class EntryRepo(Protocol):
    """Repository contract for lane entries (the searchable atoms)."""

    entries: dict[str, Entry]

    def get_entry(self, entry_id: str) -> Entry | None: ...

    def list_entries(
        self, where: Mapping[str, Any] | None = None, *, lane: str | None = None
    ) -> dict[str, Entry]: ...

    def clear_entries(
        self, where: Mapping[str, Any] | None = None, *, lane: str | None = None
    ) -> dict[str, Entry]: ...

    def create_entry(
        self,
        *,
        lane: str,
        source_id: str | None,
        entry_kind: str,
        text: str,
        embedding: list[float],
        user_data: dict[str, Any],
        source_path: str | None = None,
        reinforce: bool = False,
        tool_record: dict[str, Any] | None = None,
    ) -> Entry: ...

    def update_entry(
        self,
        *,
        entry_id: str,
        entry_kind: str | None = None,
        text: str | None = None,
        embedding: list[float] | None = None,
        extra: dict[str, Any] | None = None,
        tool_record: dict[str, Any] | None = None,
    ) -> Entry: ...

    def delete_entry(self, entry_id: str) -> None: ...

    def list_entries_by_ref_ids(
        self, ref_ids: list[str], where: Mapping[str, Any] | None = None
    ) -> dict[str, Entry]: ...

    def vector_search_entries(
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
        *,
        lane: str | None = None,
        ranking: Literal["similarity", "salience"] = "similarity",
        recency_decay_days: float = 30.0,
    ) -> list[tuple[str, float]]: ...

    def load_existing(self) -> None: ...
