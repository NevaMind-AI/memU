from __future__ import annotations

from typing import Protocol, runtime_checkable

from memu.database.models import RecallEntry as RecallEntryRecord
from memu.database.models import RecallFile as RecallFileRecord
from memu.database.models import RecallFileEntry as RecallFileEntryRecord
from memu.database.models import Resource as ResourceRecord
from memu.database.repositories import RecallEntryRepo, RecallFileEntryRepo, RecallFileRepo, ResourceRepo


@runtime_checkable
class Database(Protocol):
    """Backend-agnostic database contract."""

    resource_repo: ResourceRepo
    recall_file_repo: RecallFileRepo
    recall_entry_repo: RecallEntryRepo
    recall_file_entry_repo: RecallFileEntryRepo

    resources: dict[str, ResourceRecord]
    items: dict[str, RecallEntryRecord]
    categories: dict[str, RecallFileRecord]
    relations: list[RecallFileEntryRecord]

    def close(self) -> None: ...


__all__ = [
    "Database",
    "RecallEntryRecord",
    "RecallFileEntryRecord",
    "RecallFileRecord",
    "ResourceRecord",
]
