from __future__ import annotations

import uuid

from memu.models import CategoryItem, MemoryCategory, MemoryItem, MemoryType, Resource


class InMemoryStore:
    def __init__(self) -> None:
        self.resources: dict[str, Resource] = {}
        self.items: dict[str, MemoryItem] = {}
        self.categories: dict[str, MemoryCategory] = {}
        self.relations: list[CategoryItem] = []

    def create_resource(self, *, url: str, modality: str, local_path: str) -> Resource:
        rid = str(uuid.uuid4())
        res = Resource(id=rid, url=url, modality=modality, local_path=local_path)
        self.resources[rid] = res
        return res

    def get_or_create_category(self, *, name: str, description: str, embedding: list[float]) -> MemoryCategory:
        for c in self.categories.values():
            if c.name == name:
                if not c.embedding:
                    c.embedding = embedding
                if not c.description:
                    c.description = description
                return c
        cid = str(uuid.uuid4())
        cat = MemoryCategory(id=cid, name=name, description=description, embedding=embedding)
        self.categories[cid] = cat
        return cat

    def create_item(
        self, *, resource_id: str, memory_type: MemoryType, summary: str, embedding: list[float]
    ) -> MemoryItem:
        mid = str(uuid.uuid4())
        it = MemoryItem(
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
        rel = CategoryItem(item_id=item_id, category_id=cat_id)
        self.relations.append(rel)
        return rel
