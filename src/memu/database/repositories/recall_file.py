from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from memu.database.models import RecallFile


@runtime_checkable
class RecallFileRepo(Protocol):
    """Repository contract for recall files."""

    recall_files: dict[str, RecallFile]

    def list_recall_files(self, where: Mapping[str, Any] | None = None) -> dict[str, RecallFile]: ...

    def clear_recall_files(self, where: Mapping[str, Any] | None = None) -> dict[str, RecallFile]: ...

    def get_or_create_recall_file(
        self,
        *,
        name: str,
        description: str,
        embedding: list[float],
        user_data: dict[str, Any],
        track: str = "memory",
    ) -> RecallFile: ...

    def update_recall_file(
        self,
        *,
        recall_file_id: str,
        name: str | None = None,
        description: str | None = None,
        embedding: list[float] | None = None,
        content: str | None = None,
    ) -> RecallFile: ...

    def load_existing(self) -> None: ...
