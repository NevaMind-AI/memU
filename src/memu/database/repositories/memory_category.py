from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from memu.database.models import MemoryCategory


@runtime_checkable
class MemoryCategoryRepo(Protocol):
    """Repository contract for memory categories."""

    categories: dict[str, MemoryCategory]

    def list_categories(self, where: Mapping[str, Any] | None = None) -> dict[str, MemoryCategory]: ...

    def get_or_create_category(self, *, name: str, description: str, embedding: list[float]) -> MemoryCategory: ...

    def load_existing(self) -> None: ...
