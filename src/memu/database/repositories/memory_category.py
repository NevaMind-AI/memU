from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from memu.database.models import MemoryCategory


@runtime_checkable
class MemoryCategoryRepo(Protocol):
    """Repository contract for memory categories."""

    categories: dict[str, MemoryCategory]

    def list_categories(self, where: Mapping[str, Any] | None = None) -> dict[str, MemoryCategory]: ...

    def get_or_create_category(
        self, *, name: str, description: str, embedding: list[float], user_data: dict[str, Any]
    ) -> MemoryCategory: ...

    def update_category(
        self,
        *,
        category_id: str,
        name: str | None = None,
        description: str | None = None,
        embedding: list[float] | None = None,
        summary: str | None = None,
    ) -> MemoryCategory: ...

    def load_existing(self) -> None: ...
