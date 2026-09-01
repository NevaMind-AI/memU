from __future__ import annotations

from dataclasses import dataclass, field

from memu.database.models import (
    RecallFile,
    RecallFileSegment,
    Resource,
)


@dataclass
class DatabaseState:
    resources: dict[str, Resource] = field(default_factory=dict)
    recall_files: dict[str, RecallFile] = field(default_factory=dict)
    segments: list[RecallFileSegment] = field(default_factory=list)
    embedding_space: str | None = None
    expected_embedding_space: str | None = None


__all__ = ["DatabaseState"]
