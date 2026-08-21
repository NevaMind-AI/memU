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
        local_path: str,
        caption: str | None,
        embedding: list[float] | None,
        user_data: dict[str, Any],
        track: str | None = None,
    ) -> Resource: ...

    def update_resource(
        self,
        *,
        resource_id: str,
        local_path: str,
        caption: str | None,
        embedding: list[float] | None,
        track: str | None = None,
    ) -> Resource:
        """Overwrite a resource's mutable fields in place, keeping ``id`` and ``created_at``.

        Unlike :meth:`RecallFileRepo.update_recall_file`, every field is written as
        given: ``None`` clears the column rather than leaving it alone. A resource is
        wholly defined by the record that carries it, so a record with no description
        drops the stored caption along with its vector.

        Raises:
            KeyError: If no resource has that id.
        """
        ...

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
