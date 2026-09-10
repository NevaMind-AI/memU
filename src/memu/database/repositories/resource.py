from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from memu.database.models import Resource
from memu.hybrid import maybe_hybrid_topk
from memu.vector import cosine_topk


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
        *,
        query_text: str | None = None,
    ) -> list[tuple[str, float]]:
        """Rank resources by cosine, optionally fused with BM25 over ``caption``.

        Returns ``(resource_id, score)`` pairs, best first, at most ``top_k``.
        ``query_text=None`` is cosine-only. All three backends already scan the
        scoped pool in Python, so hybrid uses that whole pool (ADR 0019).
        Resources without an embedding are skipped by cosine; they can still
        surface through BM25 when ``caption`` matches.
        """
        pool = self.list_resources(where)
        cosine_k = len(pool) if query_text and query_text.strip() else top_k
        ranked = cosine_topk(
            query_vec,
            [(rid, res.embedding) for rid, res in pool.items() if res.embedding],
            k=cosine_k,
        )
        return maybe_hybrid_topk(
            query_text=query_text,
            cosine_hits=ranked,
            texts={rid: res.caption or "" for rid, res in pool.items()},
            top_k=top_k,
        )

    def load_existing(self) -> None: ...
