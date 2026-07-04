from __future__ import annotations

from dataclasses import dataclass, field

from memu.database.models import (
    RecallEntry,
    RecallFile,
    RecallFileEntry,
    RecallFileResource,
    RecallFileSegment,
    Resource,
)


@dataclass
class DatabaseState:
    resources: dict[str, Resource] = field(default_factory=dict)
    items: dict[str, RecallEntry] = field(default_factory=dict)
    categories: dict[str, RecallFile] = field(default_factory=dict)
    relations: list[RecallFileEntry] = field(default_factory=list)
    resource_relations: list[RecallFileResource] = field(default_factory=list)
    segments: list[RecallFileSegment] = field(default_factory=list)


__all__ = ["DatabaseState"]
