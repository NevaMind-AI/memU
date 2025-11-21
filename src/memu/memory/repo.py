from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

from memu.models import CategoryItem, MemoryCategory, MemoryItem, MemoryType, Resource

if TYPE_CHECKING:
    from memu.storage.sqlite_db import SQLiteDB
    from memu.storage.vector_db import SimpleVectorDB


class PersistentStore:
    """Persistent storage backed by SQLite and vector DB."""

    def __init__(
        self,
        *,
        db: SQLiteDB,
        vector_db: SimpleVectorDB,
        user_id: str,
        agent_id: str,
    ) -> None:
        self.db = db
        self.vector_db = vector_db
        self.user_id = user_id
        self.agent_id = agent_id

        # In-memory caches for fast access
        self.resources: dict[str, Resource] = {}
        self.items: dict[str, MemoryItem] = {}
        self.categories: dict[str, MemoryCategory] = {}
        self.relations: list[CategoryItem] = []

        self._load_from_db()

    def _load_from_db(self) -> None:
        """Load data from database into memory."""
        # Load resources
        for res in self.db.list_resources(self.user_id, self.agent_id):
            # Load embeddings from vector DB
            embedding = self.vector_db.get("resources", res.id, self.user_id, self.agent_id)
            if embedding:
                res.embedding = embedding
            self.resources[res.id] = res

        # Load categories
        for cat in self.db.list_categories(self.user_id, self.agent_id):
            # Load embeddings from vector DB
            embedding = self.vector_db.get("categories", cat.id, self.user_id, self.agent_id)
            if embedding:
                cat.embedding = embedding
            self.categories[cat.id] = cat

        # Load items
        for item in self.db.list_items(self.user_id, self.agent_id):
            # Load embeddings from vector DB
            embedding = self.vector_db.get("items", item.id, self.user_id, self.agent_id)
            if embedding:
                item.embedding = embedding
            self.items[item.id] = item

        # Load relationships
        self.relations = self.db.list_category_items(self.user_id, self.agent_id)

    def create_resource(self, *, url: str, modality: str, local_path: str) -> Resource:
        """Create a new resource."""
        rid = str(uuid.uuid7())
        res = Resource(
            id=rid,
            user_id=self.user_id,
            agent_id=self.agent_id,
            url=url,
            modality=modality,
            local_path=local_path,
            created_at=time.time(),
        )
        self.db.create_resource(res)
        self.resources[rid] = res
        return res

    def get_or_create_category(self, *, name: str, description: str, embedding: list[float]) -> MemoryCategory:
        """Get or create a category."""
        # Check in-memory cache first
        for c in self.categories.values():
            if c.name == name:
                if not c.embedding:
                    c.embedding = embedding
                    # Update vector DB with text
                    text = f"{name}: {description}" if description else name
                    self.vector_db.upsert("categories", c.id, embedding, self.user_id, self.agent_id, text=text)
                if not c.description:
                    c.description = description
                    self.db.create_category(c)
                return c

        # Check database
        existing = self.db.get_category_by_name(name, self.user_id, self.agent_id)
        if existing:
            existing.embedding = embedding
            text = f"{name}: {description}" if description else name
            self.vector_db.upsert("categories", existing.id, embedding, self.user_id, self.agent_id, text=text)
            self.categories[existing.id] = existing
            return existing

        # Create new category
        cid = str(uuid.uuid7())
        cat = MemoryCategory(
            id=cid,
            user_id=self.user_id,
            agent_id=self.agent_id,
            name=name,
            description=description,
            embedding=embedding,
            created_at=time.time(),
        )
        self.db.create_category(cat)
        text = f"{name}: {description}" if description else name
        self.vector_db.upsert("categories", cid, embedding, self.user_id, self.agent_id, text=text)
        self.categories[cid] = cat
        return cat

    def create_item(
        self, *, resource_id: str, memory_type: MemoryType, summary: str, embedding: list[float]
    ) -> MemoryItem:
        """Create a new memory item."""
        mid = str(uuid.uuid7())
        it = MemoryItem(
            id=mid,
            user_id=self.user_id,
            agent_id=self.agent_id,
            resource_id=resource_id,
            memory_type=memory_type,
            summary=summary,
            embedding=embedding,
            created_at=time.time(),
        )
        self.db.create_item(it)
        # Store embedding with summary text
        self.vector_db.upsert("items", mid, embedding, self.user_id, self.agent_id, text=summary)
        self.items[mid] = it
        return it

    def link_item_category(self, item_id: str, cat_id: str) -> CategoryItem:
        """Link an item to a category."""
        _ = self.items[item_id]
        for rel in self.relations:
            if rel.item_id == item_id and rel.category_id == cat_id:
                return rel
        rel = CategoryItem(
            item_id=item_id,
            category_id=cat_id,
            user_id=self.user_id,
            agent_id=self.agent_id,
        )
        self.db.create_category_item(rel)
        self.relations.append(rel)
        return rel

    def update_resource_embedding(self, resource_id: str, embedding: list[float]) -> None:
        """Update resource embedding."""
        res = self.resources.get(resource_id)
        if res:
            res.embedding = embedding
            # Store embedding with caption text
            text = res.caption if res.caption else res.url
            self.vector_db.upsert("resources", resource_id, embedding, self.user_id, self.agent_id, text=text)

    def update_category_summary(self, category_id: str, summary: str) -> None:
        """Update category summary."""
        cat = self.categories.get(category_id)
        if cat:
            cat.summary = summary
            self.db.update_category_summary(category_id, summary, self.user_id, self.agent_id)


class InMemoryStore:
    """Legacy in-memory store for backward compatibility."""

    def __init__(self) -> None:
        self.resources: dict[str, Resource] = {}
        self.items: dict[str, MemoryItem] = {}
        self.categories: dict[str, MemoryCategory] = {}
        self.relations: list[CategoryItem] = []

    def create_resource(
        self, *, url: str, modality: str, local_path: str, user_id: str = "default", agent_id: str = "default"
    ) -> Resource:
        rid = str(uuid.uuid7())
        res = Resource(
            id=rid,
            user_id=user_id,
            agent_id=agent_id,
            url=url,
            modality=modality,
            local_path=local_path,
            created_at=time.time(),
        )
        self.resources[rid] = res
        return res

    def get_or_create_category(
        self,
        *,
        name: str,
        description: str,
        embedding: list[float],
        user_id: str = "default",
        agent_id: str = "default",
    ) -> MemoryCategory:
        for c in self.categories.values():
            if c.name == name:
                if not c.embedding:
                    c.embedding = embedding
                if not c.description:
                    c.description = description
                return c
        cid = str(uuid.uuid7())
        cat = MemoryCategory(
            id=cid,
            user_id=user_id,
            agent_id=agent_id,
            name=name,
            description=description,
            embedding=embedding,
            created_at=time.time(),
        )
        self.categories[cid] = cat
        return cat

    def create_item(
        self,
        *,
        resource_id: str,
        memory_type: MemoryType,
        summary: str,
        embedding: list[float],
        user_id: str = "default",
        agent_id: str = "default",
    ) -> MemoryItem:
        mid = str(uuid.uuid7())
        it = MemoryItem(
            id=mid,
            user_id=user_id,
            agent_id=agent_id,
            resource_id=resource_id,
            memory_type=memory_type,
            summary=summary,
            embedding=embedding,
            created_at=time.time(),
        )
        self.items[mid] = it
        return it

    def link_item_category(
        self, item_id: str, cat_id: str, user_id: str = "default", agent_id: str = "default"
    ) -> CategoryItem:
        _ = self.items[item_id]
        for rel in self.relations:
            if rel.item_id == item_id and rel.category_id == cat_id:
                return rel
        rel = CategoryItem(
            item_id=item_id,
            category_id=cat_id,
            user_id=user_id,
            agent_id=agent_id,
        )
        self.relations.append(rel)
        return rel
