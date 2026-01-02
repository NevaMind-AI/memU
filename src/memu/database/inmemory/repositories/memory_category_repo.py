from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

import pendulum

from memu.database.inmemory.repositories.filter import matches_where
from memu.database.inmemory.state import InMemoryState
from memu.database.models import MemoryCategory
from memu.database.repositories.memory_category import MemoryCategoryRepo as MemoryCategoryRepoProtocol


class InMemoryMemoryCategoryRepository(MemoryCategoryRepoProtocol):
    def __init__(self, *, state: InMemoryState, memory_category_model: type[MemoryCategory]) -> None:
        self._state = state
        self.memory_category_model = memory_category_model
        self.categories: dict[str, MemoryCategory] = self._state.categories

    def list_categories(self, where: Mapping[str, Any] | None = None) -> dict[str, MemoryCategory]:
        if not where:
            return dict(self.categories)
        return {cid: cat for cid, cat in self.categories.items() if matches_where(cat, where)}

    def get_or_create_category(
        self, *, name: str, description: str, embedding: list[float], user_data: dict[str, Any]
    ) -> MemoryCategory:
        for c in self.categories.values():
            if c.name == name and all(getattr(c, k) == v for k, v in user_data.items()):
                now = pendulum.now("UTC")
                if c.embedding is None:
                    c.embedding = embedding
                    c.updated_at = now
                if not c.description:
                    c.description = description
                    c.updated_at = now
                return c
        cid = str(uuid.uuid4())
        cat = self.memory_category_model(id=cid, name=name, description=description, embedding=embedding, **user_data)
        self.categories[cid] = cat
        return cat

    def update_category(
        self,
        *,
        category_id: str,
        name: str | None = None,
        description: str | None = None,
        embedding: list[float] | None = None,
        summary: str | None = None,
    ) -> MemoryCategory:
        cat = self.categories.get(category_id)
        if cat is None:
            msg = f"Category with id {category_id} not found"
            raise KeyError(msg)

        if name is not None:
            cat.name = name
        if description is not None:
            cat.description = description
        if embedding is not None:
            cat.embedding = embedding
        if summary is not None:
            cat.summary = summary

        cat.updated_at = pendulum.now("UTC")
        return cat

    def load_existing(self) -> None:
        return None


MemoryCategoryRepo = InMemoryMemoryCategoryRepository

__all__ = ["InMemoryMemoryCategoryRepository", "MemoryCategoryRepo"]
