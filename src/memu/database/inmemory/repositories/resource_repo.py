from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from memu.database.inmemory.repositories.filter import matches_where
from memu.database.inmemory.state import InMemoryState
from memu.database.models import Resource
from memu.database.repositories.resource import ResourceRepo as ResourceRepoProtocol
from memu.vector import cosine_topk


class InMemoryResourceRepository(ResourceRepoProtocol):
    def __init__(self, *, state: InMemoryState, resource_model: type[Resource]) -> None:
        self._state = state
        self.resource_model = resource_model
        self.resources: dict[str, Resource] = self._state.resources

    def list_resources(self, where: Mapping[str, Any] | None = None) -> dict[str, Resource]:
        if not where:
            return dict(self.resources)
        return {rid: res for rid, res in self.resources.items() if matches_where(res, where)}

    def clear_resources(self, where: Mapping[str, Any] | None = None) -> dict[str, Resource]:
        if not where:
            matches = self.resources.copy()
            self.resources.clear()
            return matches
        matches = {rid: res for rid, res in self.resources.items() if matches_where(res, where)}
        for rid in matches:
            self.resources.pop(rid, None)
        return matches

    def delete_resource(self, resource_id: str) -> None:
        self.resources.pop(resource_id, None)

    def create_resource(
        self,
        *,
        url: str,
        modality: str,
        local_path: str,
        caption: str | None,
        embedding: list[float] | None,
        user_data: dict[str, Any],
    ) -> Resource:
        rid = str(uuid.uuid4())
        res = self.resource_model(
            id=rid,
            url=url,
            modality=modality,
            local_path=local_path,
            caption=caption,
            embedding=embedding,
            **user_data,
        )
        self.resources[rid] = res
        return res

    def vector_search_resources(
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        pool = self.list_resources(where)
        corpus = [(rid, res.embedding) for rid, res in pool.items() if res.embedding]
        return cosine_topk(query_vec, corpus, k=top_k)

    def load_existing(self) -> None:
        return None


ResourceRepo = InMemoryResourceRepository

__all__ = ["InMemoryResourceRepository", "ResourceRepo"]
