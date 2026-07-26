from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from memu.database.models import RecallFile


@runtime_checkable
class RecallFileRepo(Protocol):
    """Repository contract for recall files."""

    recall_files: dict[str, RecallFile]

    def list_recall_files(self, where: Mapping[str, Any] | None = None) -> dict[str, RecallFile]: ...

    def list_recall_files_page(
        self,
        where: Mapping[str, Any] | None,
        *,
        after: tuple[str, str, str] | None,
        limit: int,
    ) -> tuple[list[RecallFile], tuple[str, str, str] | None]:
        """One keyset page ordered by ``(track, name, id)``, plus the next cursor.

        Returns the ordered page and the ``(track, name, id)`` of its last row
        when more rows remain, or ``None`` on the final page. Distinct from
        :meth:`list_recall_files`, which returns the whole unordered mapping its
        roll-up and commit callers need — this one is the paginated read behind
        ``list_all_recall_files`` (see ADR 0014).
        """
        ...

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
