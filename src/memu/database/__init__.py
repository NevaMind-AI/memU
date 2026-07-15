"""Storage backends for MemU."""

from memu.database.factory import build_database
from memu.database.interfaces import (
    Database,
    RecallFileRecord,
    RecallFileResourceRecord,
    RecallFileSegmentRecord,
    ResourceRecord,
)
from memu.database.repositories import (
    RecallFileRepo,
    RecallFileResourceRepo,
    RecallFileSegmentRepo,
    ResourceRepo,
)

__all__ = [
    "Database",
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
