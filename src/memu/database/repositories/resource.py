from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from memu.database.models import Resource


@runtime_checkable
class ResourceRepo(Protocol):
    """Repository contract for resource records."""

    resources: dict[str, Resource]

    def list_resources(self, where: Mapping[str, Any] | None = None) -> dict[str, Resource]: ...

    def clear_resources(self, where: Mapping[str, Any] | None = None) -> dict[str, Resource]: ...

    def delete_resource(self, resource_id: str) -> None: ...

    def create_resource(
        self,
        *,
        url: str,
        modality: str,
        local_path: str,
        caption: str | None,
        embedding: list[float] | None,
        user_data: dict[str, Any],
    ) -> Resource: ...

    def vector_search_resources(
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        """Rank resources by cosine similarity of their stored embeddings.

        Returns a list of ``(resource_id, score)`` tuples ordered by descending
        similarity. Resources without an embedding are skipped.
        """
        ...

    def load_existing(self) -> None: ...
