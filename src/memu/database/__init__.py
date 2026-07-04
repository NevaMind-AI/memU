"""Storage backends for MemU."""

from memu.database.factory import build_database
from memu.database.interfaces import (
    Database,
    RecallEntryRecord,
    RecallFileEntryRecord,
    RecallFileRecord,
    RecallFileResourceRecord,
    RecallFileSegmentRecord,
    ResourceRecord,
)
from memu.database.repositories import (
    RecallEntryRepo,
    RecallFileEntryRepo,
    RecallFileRepo,
    RecallFileResourceRepo,
    RecallFileSegmentRepo,
    ResourceRepo,
)

__all__ = [
    "Database",
    "RecallEntryRecord",
    "RecallEntryRepo",
    "RecallFileEntryRecord",
    "RecallFileEntryRepo",
    "RecallFileRecord",
    "RecallFileRepo",
    "RecallFileResourceRecord",
    "RecallFileResourceRepo",
    "RecallFileSegmentRecord",
    "RecallFileSegmentRepo",
    "ResourceRecord",
    "ResourceRepo",
    "build_database",
    "inmemory",
    "postgres",
    "schema",
    "sqlite",
]
