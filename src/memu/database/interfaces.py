from __future__ import annotations

from typing import Protocol, runtime_checkable

from memu.database.models import RecallFile as RecallFileRecord
from memu.database.models import RecallFileSegment as RecallFileSegmentRecord
from memu.database.models import Resource as ResourceRecord
from memu.database.repositories import (
    RecallFileRepo,
    RecallFileSegmentRepo,
    ResourceRepo,
)


@runtime_checkable
class Database(Protocol):
    """Backend-agnostic database contract."""

    resource_repo: ResourceRepo
    recall_file_repo: RecallFileRepo
    recall_file_segment_repo: RecallFileSegmentRepo

    resources: dict[str, ResourceRecord]
    recall_files: dict[str, RecallFileRecord]
    segments: list[RecallFileSegmentRecord]

    def close(self) -> None: ...


__all__ = [
    "Database",
    "RecallFileRecord",
    "RecallFileSegmentRecord",
    "ResourceRecord",
]
