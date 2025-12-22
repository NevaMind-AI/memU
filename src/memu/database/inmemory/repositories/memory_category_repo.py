from __future__ import annotations

import uuid

import pendulum

from memu.database.inmemory.state import InMemoryState
from memu.database.models import MemoryCategory
from memu.database.repositories.memory_category import MemoryCategoryRepo as MemoryCategoryRepoProtocol


class InMemoryMemoryCategoryRepository(MemoryCategoryRepoProtocol):
    def __init__(self, *, state: InMemoryState, memory_category_model: type[MemoryCategory]) -> None:
        self._state = state
        self.memory_category_model = memory_category_model
        self.categories: dict[str, MemoryCategory] = self._state.categories

    def get_or_create_category(self, *, name: str, description: str, embedding: list[float]) -> MemoryCategory:
        for c in self.categories.values():
            if c.name == name:
                now = pendulum.now("UTC")
                if not c.embedding:
                    c.embedding = embedding
                    c.updated_at = now
                if not c.description:
                    c.description = description
                    c.updated_at = now
                return c
        cid = str(uuid.uuid4())
        cat = self.memory_category_model(id=cid, name=name, description=description, embedding=embedding)
        self.categories[cid] = cat
        return cat

    def load_existing(self) -> None:
        return None


MemoryCategoryRepo = InMemoryMemoryCategoryRepository

__all__ = ["InMemoryMemoryCategoryRepository", "MemoryCategoryRepo"]
