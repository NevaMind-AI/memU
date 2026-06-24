from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from memu.database.models import Resource


@runtime_checkable
class ResourceRepo(Protocol):
    """Repository contract for resource records (raw inputs and generated lane docs)."""

    resources: dict[str, Resource]

    def get_resource(self, resource_id: str) -> Resource | None: ...

    def list_resources(
        self, where: Mapping[str, Any] | None = None, *, lane: str | None = None
    ) -> dict[str, Resource]: ...

    def clear_resources(
        self, where: Mapping[str, Any] | None = None, *, lane: str | None = None
    ) -> dict[str, Resource]: ...

    def delete_resource(self, resource_id: str) -> None: ...

    def create_resource(
        self,
        *,
        modality: str,
        user_data: dict[str, Any],
        lane: str = "source",
        url: str | None = None,
        local_path: str | None = None,
        slug: str | None = None,
        title: str | None = None,
        description: str | None = None,
        content: str | None = None,
        summary: str | None = None,
        embedding: list[float] | None = None,
        resource_refs: list[dict[str, Any]] | None = None,
    ) -> Resource: ...

    def get_or_create_doc(
        self,
        *,
        lane: str,
        title: str,
        description: str,
        embedding: list[float],
        user_data: dict[str, Any],
        slug: str | None = None,
    ) -> Resource:
        """Get an existing generated doc by ``(lane, title, scope)`` or create one."""
        ...

    def update_resource(
        self,
        *,
        resource_id: str,
        title: str | None = None,
        description: str | None = None,
        content: str | None = None,
        summary: str | None = None,
        embedding: list[float] | None = None,
        resource_refs: list[dict[str, Any]] | None = None,
    ) -> Resource: ...

    def vector_search_resources(
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
        *,
        lane: str | None = None,
    ) -> list[tuple[str, float]]:
        """Rank resources by cosine similarity of their stored embeddings.

        Returns ``(resource_id, score)`` ordered by descending similarity;
        resources without an embedding are skipped.
        """
        ...

    def load_existing(self) -> None: ...
