from __future__ import annotations

from typing import Protocol, runtime_checkable

from memu.database.models import CategoryItem as CategoryItemRecord
from memu.database.models import MemoryCategory as MemoryCategoryRecord
from memu.database.models import MemoryItem as MemoryItemRecord
from memu.database.models import Resource as ResourceRecord
from memu.database.repositories import CategoryItemRepo, MemoryCategoryRepo, MemoryItemRepo, ResourceRepo


@runtime_checkable
class Database(Protocol):
    """Backend-agnostic database contract."""

    resource_repo: ResourceRepo
    memory_category_repo: MemoryCategoryRepo
    memory_item_repo: MemoryItemRepo
    category_item_repo: CategoryItemRepo

    resources: dict[str, ResourceRecord]
    items: dict[str, MemoryItemRecord]
    categories: dict[str, MemoryCategoryRecord]
    relations: list[CategoryItemRecord]

    def close(self) -> None: ...


@runtime_checkable
class AsyncDatabase(Protocol):
    """Async database contract with async close method."""

    resource_repo: ResourceRepo
    memory_category_repo: MemoryCategoryRepo
    memory_item_repo: MemoryItemRepo
    category_item_repo: CategoryItemRepo

    resources: dict[str, ResourceRecord]
    items: dict[str, MemoryItemRecord]
    categories: dict[str, MemoryCategoryRecord]
    relations: list[CategoryItemRecord]

    def close(self) -> None: ...

    async def close_async(self) -> None: ...


__all__ = [
    "AsyncDatabase",
    "CategoryItemRecord",
    "Database",
    "MemoryCategoryRecord",
    "MemoryItemRecord",
    "ResourceRecord",
]
