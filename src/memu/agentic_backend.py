from __future__ import annotations

from typing import Any, Protocol


class AgenticMemoryBackend(Protocol):
    """The three memory capabilities consumed by CLIs and host adapters.

    ``MemoryService`` satisfies this protocol structurally for local execution.
    Remote implementations can provide the same surface without adding transport
    concerns to the local service composition root.
    """

    async def list_all_recall_files(
        self,
        where: dict[str, Any] | None = None,
        *,
        cursor: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """One keyset page of recall files with an opaque ``next_cursor`` (ADR 0014).

        ``next_cursor`` is ``None`` on the last page; callers follow it to
        reassemble the full set. Both backends order identically, so the two
        execution paths stay byte-for-byte the same.
        """
        ...

    async def progressive_retrieve(
        self,
        query: str,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    async def commit_results(
        self,
        *,
        recall_files: list[dict[str, Any]] | None = None,
        resource: list[dict[str, Any]] | None = None,
        user: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...
