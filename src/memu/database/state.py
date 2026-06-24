from __future__ import annotations

from dataclasses import dataclass, field

from memu.database.models import Entry, Resource, ResourceEntry


@dataclass
class DatabaseState:
    resources: dict[str, Resource] = field(default_factory=dict)
    entries: dict[str, Entry] = field(default_factory=dict)
    relations: list[ResourceEntry] = field(default_factory=list)


__all__ = ["DatabaseState"]
