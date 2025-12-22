from __future__ import annotations

from typing import Protocol, runtime_checkable

from memu.database.models import CategoryItem


@runtime_checkable
class CategoryItemRepo(Protocol):
    """Repository contract for item/category relations."""

    relations: list[CategoryItem]

    def link_item_category(self, item_id: str, cat_id: str) -> CategoryItem: ...

    def load_existing(self) -> None: ...
