from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock

from memu.database.models import (
    RecallFile,
    RecallFileSegment,
    Resource,
)


@dataclass
class DatabaseState:
    lock: RLock = field(default_factory=RLock, repr=False)
    resources: dict[str, Resource] = field(default_factory=dict)
    recall_files: dict[str, RecallFile] = field(default_factory=dict)
    segments: list[RecallFileSegment] = field(default_factory=list)


__all__ = ["DatabaseState"]
