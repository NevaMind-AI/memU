from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from memu.database.models import RecallFile


@runtime_checkable
class RecallFileRepo(Protocol):
    """Repository contract for memory categories."""

    categories: dict[str, RecallFile]

    def list_categories(self, where: Mapping[str, Any] | None = None) -> dict[str, RecallFile]: ...

    def clear_categories(self, where: Mapping[str, Any] | None = None) -> dict[str, RecallFile]: ...

    def get_or_create_category(
        self,
        *,
        name: str,
        description: str,
        embedding: list[float],
        user_data: dict[str, Any],
        track: str = "memory",
    ) -> RecallFile: ...

    def update_category(
        self,
        *,
        category_id: str,
        name: str | None = None,
        description: str | None = None,
        embedding: list[float] | None = None,
        content: str | None = None,
    ) -> RecallFile: ...

    def load_existing(self) -> None: ...
