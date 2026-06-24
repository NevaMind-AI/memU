from __future__ import annotations

from typing import Protocol, runtime_checkable

from memu.database.models import Entry as EntryRecord
from memu.database.models import Resource as ResourceRecord
from memu.database.models import ResourceEntry as ResourceEntryRecord
from memu.database.repositories import EntryRepo, ResourceEntryRepo, ResourceRepo


@runtime_checkable
class Database(Protocol):
    """Backend-agnostic database contract."""

    resource_repo: ResourceRepo
    entry_repo: EntryRepo
    resource_entry_repo: ResourceEntryRepo

    resources: dict[str, ResourceRecord]
    entries: dict[str, EntryRecord]
    relations: list[ResourceEntryRecord]

    def close(self) -> None: ...


__all__ = [
    "Database",
    "EntryRecord",
    "ResourceEntryRecord",
    "ResourceRecord",
]
