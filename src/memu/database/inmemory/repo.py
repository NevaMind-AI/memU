from __future__ import annotations

import time
import uuid

from pydantic import BaseModel

from memu.database.inmemory.index import cosine_topk
from memu.database.inmemory.models import (
    CategoryItem,
    MemoryCategory,
    MemoryItem,
    MemoryType,
    Resource,
)


class InMemoryStore:
    def __init__(
        self,
        *,
        base_model: type[BaseModel] | None = None,
        resource_model: type[BaseModel] | None = None,
        memory_item_model: type[BaseModel] | None = None,
        memory_category_model: type[BaseModel] | None = None,
        category_item_model: type[BaseModel] | None = None,
        scope_key: str | None = None,
    ) -> None:
        self.base_model = base_model or BaseModel
        self.resource_model = resource_model or Resource
        self.memory_item_model = memory_item_model or MemoryItem
        self.memory_category_model = memory_category_model or MemoryCategory
        self.category_item_model = category_item_model or CategoryItem
        self.scope_key = scope_key or "default"
        self.resources: dict[str, BaseModel] = {}
        self.items: dict[str, BaseModel] = {}
        self.categories: dict[str, BaseModel] = {}
        self.relations: list[BaseModel] = []

    def create_resource(self, *, url: str, modality: str, local_path: str) -> Resource:
        rid = str(uuid.uuid4())
        res = self.resource_model(id=rid, url=url, modality=modality, local_path=local_path)
        self.resources[rid] = res
        return res

    def get_or_create_category(self, *, name: str, description: str, embedding: list[float]) -> MemoryCategory:
        for c in self.categories.values():
            if c.name == name:
                if not c.embedding:
                    c.embedding = embedding
                    c.updated_at = time.time()
                if not c.description:
                    c.description = description
                    c.updated_at = time.time()
                return c
        cid = str(uuid.uuid4())
        cat = self.memory_category_model(id=cid, name=name, description=description, embedding=embedding)
        self.categories[cid] = cat
        return cat

    def create_item(
        self, *, resource_id: str, memory_type: MemoryType, summary: str, embedding: list[float]
    ) -> MemoryItem:
        mid = str(uuid.uuid4())
        it = self.memory_item_model(
            id=mid,
            resource_id=resource_id,
            memory_type=memory_type,
            summary=summary,
            embedding=embedding,
        )
        self.items[mid] = it
        return it

    def link_item_category(self, item_id: str, cat_id: str) -> CategoryItem:
        _ = self.items[item_id]
        for rel in self.relations:
            if rel.item_id == item_id and rel.category_id == cat_id:
                return rel
        rel = self.category_item_model(id=str(uuid.uuid4()), item_id=item_id, category_id=cat_id)
        self.relations.append(rel)
        return rel

    def vector_search_items(self, query_vec: list[float], top_k: int) -> list[tuple[str, float]]:
        hits = cosine_topk(query_vec, [(i.id, i.embedding) for i in self.items.values()], k=top_k)
        return hits
