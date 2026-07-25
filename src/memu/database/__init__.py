"""Storage backends for MemU."""

from memu.database.factory import build_database
from memu.database.interfaces import (
    Database,
    RecallFileRecord,
    RecallFileSegmentRecord,
    ResourceRecord,
)
from memu.database.repositories import (
    RecallFileRepo,
    RecallFileSegmentRepo,
    ResourceRepo,
)

__all__ = [
    "Database",
    "RecallFileRecord",
    "RecallFileRepo",
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
