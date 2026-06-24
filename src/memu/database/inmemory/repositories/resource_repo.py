from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

import pendulum

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

    def get_resource(self, resource_id: str) -> Resource | None:
        return self.resources.get(resource_id)

    def list_resources(self, where: Mapping[str, Any] | None = None, *, lane: str | None = None) -> dict[str, Resource]:
        result = (
            self.resources
            if not where
            else {rid: res for rid, res in self.resources.items() if matches_where(res, where)}
        )
        if lane is not None:
            result = {rid: res for rid, res in result.items() if getattr(res, "lane", "source") == lane}
        return dict(result)

    def clear_resources(
        self, where: Mapping[str, Any] | None = None, *, lane: str | None = None
    ) -> dict[str, Resource]:
        if not where and lane is None:
            matches = self.resources.copy()
            self.resources.clear()
            return matches
        matches = self.list_resources(where, lane=lane)
        for rid in matches:
            self.resources.pop(rid, None)
        return matches

    def delete_resource(self, resource_id: str) -> None:
        self.resources.pop(resource_id, None)

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
    ) -> Resource:
        rid = str(uuid.uuid4())
        res = self.resource_model(
            id=rid,
            lane=lane,
            modality=modality,
            url=url,
            local_path=local_path,
            slug=slug,
            title=title,
            description=description,
            content=content,
            summary=summary,
            embedding=embedding,
            resource_refs=resource_refs or [],
            **user_data,
        )
        self.resources[rid] = res
        return res

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
        for res in self.resources.values():
            same_lane = getattr(res, "lane", "source") == lane
            if same_lane and res.title == title and all(getattr(res, k) == v for k, v in user_data.items()):
                now = pendulum.now("UTC")
                if res.embedding is None:
                    res.embedding = embedding
                    res.updated_at = now
                if not res.description:
                    res.description = description
                    res.updated_at = now
                return res
        return self.create_resource(
            modality="markdown",
            lane=lane,
            title=title,
            slug=slug,
            description=description,
            embedding=embedding,
            user_data=user_data,
        )

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
    ) -> Resource:
        res = self.resources.get(resource_id)
        if res is None:
            msg = f"Resource with id {resource_id} not found"
            raise KeyError(msg)
        if title is not None:
            res.title = title
        if description is not None:
            res.description = description
        if content is not None:
            res.content = content
        if summary is not None:
            res.summary = summary
        if embedding is not None:
            res.embedding = embedding
        if resource_refs is not None:
            res.resource_refs = resource_refs
        res.updated_at = pendulum.now("UTC")
        return res

    def vector_search_resources(
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
        *,
        lane: str | None = None,
    ) -> list[tuple[str, float]]:
        pool = self.list_resources(where, lane=lane)
        corpus = [(rid, res.embedding) for rid, res in pool.items() if res.embedding]
        return cosine_topk(query_vec, corpus, k=top_k)

    def load_existing(self) -> None:
        return None


ResourceRepo = InMemoryResourceRepository

__all__ = ["InMemoryResourceRepository", "ResourceRepo"]
