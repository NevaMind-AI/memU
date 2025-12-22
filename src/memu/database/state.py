from __future__ import annotations

from dataclasses import dataclass, field

from memu.database.models import CategoryItem, MemoryCategory, MemoryItem, Resource


@dataclass
class DatabaseState:
    resources: dict[str, Resource] = field(default_factory=dict)
    items: dict[str, MemoryItem] = field(default_factory=dict)
    categories: dict[str, MemoryCategory] = field(default_factory=dict)
    relations: list[CategoryItem] = field(default_factory=list)


__all__ = ["DatabaseState"]
