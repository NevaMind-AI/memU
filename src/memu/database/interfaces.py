from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from memu.database.models import RecallFile as RecallFileRecord
from memu.database.models import RecallFileSegment as RecallFileSegmentRecord
from memu.database.models import Resource as ResourceRecord
from memu.database.repositories import (
    RecallFileRepo,
    RecallFileSegmentRepo,
    ResourceRepo,
)


class EmbeddingSpaceMismatch(RuntimeError):
    """The store contains vectors produced by another or unknown model."""

    def __init__(self) -> None:
        super().__init__("embedding configuration does not match this store; run `memu reindex`")


@runtime_checkable
class Database(Protocol):
    """Backend-agnostic database contract."""

    resource_repo: ResourceRepo
    recall_file_repo: RecallFileRepo
    recall_file_segment_repo: RecallFileSegmentRepo

    resources: dict[str, ResourceRecord]
    recall_files: dict[str, RecallFileRecord]
    segments: list[RecallFileSegmentRecord]

    def assert_embedding_space(self, embedding_space: str, *, initialize: bool = True) -> None: ...

    def replace_all_embeddings(
        self,
        *,
        resources: Mapping[str, list[float]],
        recall_files: Mapping[str, list[float]],
        segments: Mapping[str, list[float]],
        embedding_space: str,
    ) -> None: ...

    def close(self) -> None: ...


__all__ = [
    "Database",
    "EmbeddingSpaceMismatch",
    "RecallFileRecord",
    "RecallFileSegmentRecord",
    "ResourceRecord",
]
