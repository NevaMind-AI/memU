from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from memu.database.models import RecallFileEntry


@runtime_checkable
class RecallFileEntryRepo(Protocol):
    """Repository contract for item/category relations."""

    relations: list[RecallFileEntry]

    def list_relations(self, where: Mapping[str, Any] | None = None) -> list[RecallFileEntry]: ...

    def link_item_category(self, item_id: str, cat_id: str, user_data: dict[str, Any]) -> RecallFileEntry: ...

    def unlink_item_category(self, item_id: str, cat_id: str) -> None: ...

    def unlink_item(self, item_id: str) -> list[RecallFileEntry]:
        """Remove all relations for a given item. Returns the removed relations."""
        ...

    def clear_relations(self, where: Mapping[str, Any] | None = None) -> list[RecallFileEntry]:
        """Remove all relations matching the scope. Returns the removed relations."""
        ...

    def get_item_categories(self, item_id: str) -> list[RecallFileEntry]: ...

    def load_existing(self) -> None: ...
