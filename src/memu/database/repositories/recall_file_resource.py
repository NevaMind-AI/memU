from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from memu.database.models import RecallFileResource


@runtime_checkable
class RecallFileResourceRepo(Protocol):
    """Repository contract for resource/category relations."""

    relations: list[RecallFileResource]

    def list_relations(self, where: Mapping[str, Any] | None = None) -> list[RecallFileResource]: ...

    def link_resource_category(
        self, resource_id: str, cat_id: str, user_data: dict[str, Any]
    ) -> RecallFileResource: ...

    def unlink_resource_category(self, resource_id: str, cat_id: str) -> None: ...

    def unlink_resource(self, resource_id: str) -> list[RecallFileResource]:
        """Remove all relations for a given resource. Returns the removed relations."""
        ...

    def clear_relations(self, where: Mapping[str, Any] | None = None) -> list[RecallFileResource]:
        """Remove all relations matching the scope. Returns the removed relations."""
        ...

    def get_resource_categories(self, resource_id: str) -> list[RecallFileResource]: ...

    def load_existing(self) -> None: ...
