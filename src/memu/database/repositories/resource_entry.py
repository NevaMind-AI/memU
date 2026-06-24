from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from memu.database.models import ResourceEntry


@runtime_checkable
class ResourceEntryRepo(Protocol):
    """Repository contract for entry <-> coarse-resource membership edges."""

    relations: list[ResourceEntry]

    def list_relations(self, where: Mapping[str, Any] | None = None) -> list[ResourceEntry]: ...

    def link_entry_resource(self, entry_id: str, resource_id: str, user_data: dict[str, Any]) -> ResourceEntry: ...

    def unlink_entry_resource(self, entry_id: str, resource_id: str) -> None: ...

    def unlink_entry(self, entry_id: str) -> list[ResourceEntry]:
        """Remove all edges for a given entry. Returns the removed edges."""
        ...

    def clear_relations(self, where: Mapping[str, Any] | None = None) -> list[ResourceEntry]:
        """Remove all edges matching the scope. Returns the removed edges."""
        ...

    def get_entry_resources(self, entry_id: str) -> list[ResourceEntry]: ...

    def load_existing(self) -> None: ...
