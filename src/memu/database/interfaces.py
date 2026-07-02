from __future__ import annotations

from typing import Protocol, runtime_checkable

from memu.database.models import RecallEntry as RecallEntryRecord
from memu.database.models import RecallFile as RecallFileRecord
from memu.database.models import RecallFileEntry as RecallFileEntryRecord
from memu.database.models import RecallFileResource as RecallFileResourceRecord
from memu.database.models import RecallFileSegment as RecallFileSegmentRecord
from memu.database.models import Resource as ResourceRecord
from memu.database.repositories import (
    RecallEntryRepo,
    RecallFileEntryRepo,
    RecallFileRepo,
    RecallFileResourceRepo,
    RecallFileSegmentRepo,
    ResourceRepo,
)


@runtime_checkable
class Database(Protocol):
    """Backend-agnostic database contract."""

    resource_repo: ResourceRepo
    recall_file_repo: RecallFileRepo
    recall_entry_repo: RecallEntryRepo
    recall_file_entry_repo: RecallFileEntryRepo
    recall_file_resource_repo: RecallFileResourceRepo
    recall_file_segment_repo: RecallFileSegmentRepo

    resources: dict[str, ResourceRecord]
    items: dict[str, RecallEntryRecord]
    categories: dict[str, RecallFileRecord]
    relations: list[RecallFileEntryRecord]
    resource_relations: list[RecallFileResourceRecord]
    segments: list[RecallFileSegmentRecord]

    def close(self) -> None: ...


__all__ = [
    "Database",
    "RecallEntryRecord",
    "RecallFileEntryRecord",
    "RecallFileRecord",
    "RecallFileResourceRecord",
    "RecallFileSegmentRecord",
    "ResourceRecord",
]
