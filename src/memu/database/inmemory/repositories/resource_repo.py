from __future__ import annotations

import uuid

from memu.database.inmemory.state import InMemoryState
from memu.database.models import Resource
from memu.database.repositories.resource import ResourceRepo as ResourceRepoProtocol


class InMemoryResourceRepository(ResourceRepoProtocol):
    def __init__(self, *, state: InMemoryState, resource_model: type[Resource]) -> None:
        self._state = state
        self.resource_model = resource_model
        self.resources: dict[str, Resource] = self._state.resources

    def create_resource(self, *, url: str, modality: str, local_path: str) -> Resource:
        rid = str(uuid.uuid4())
        res = self.resource_model(id=rid, url=url, modality=modality, local_path=local_path)
        self.resources[rid] = res
        return res

    def load_existing(self) -> None:
        return None


ResourceRepo = InMemoryResourceRepository

__all__ = ["InMemoryResourceRepository", "ResourceRepo"]
