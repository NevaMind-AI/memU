from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class VectorIndex(Protocol):
    """Backend-agnostic external vector index contract.

    Implementations keep vectors synchronized with the metadata store:
    writes (``upsert`` / ``delete``) mirror mutations on memory items,
    and ``search`` replaces the metadata backend's own top-k computation.
    Filtering uses the same scope keys (``user_id``, ``agent_id``, ...) the
    metadata store uses in its ``where`` clauses.
    """

    def upsert(
        self,
        item_id: str,
        vector: list[float],
        scope: Mapping[str, Any] | None = None,
    ) -> None: ...

    def delete(self, item_id: str) -> None: ...

    def delete_many(self, item_ids: Iterable[str]) -> None: ...

    def search(
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
    ) -> list[tuple[str, float]]: ...

    def close(self) -> None: ...


__all__ = ["VectorIndex"]
