from __future__ import annotations

import pathlib
import sqlite3
import time

from memu.models import CategoryItem, MemoryCategory, MemoryItem, Resource


class SQLiteDB:
    """SQLite database storage for memory components."""

    def __init__(self, db_path: str):
        self.db_path = pathlib.Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize database schema."""
        cursor = self.conn.cursor()

        # Resources table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resources (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                url TEXT NOT NULL,
                modality TEXT NOT NULL,
                local_path TEXT NOT NULL,
                caption TEXT,
                created_at REAL NOT NULL,
                UNIQUE(user_id, agent_id, url)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_resources_user_agent ON resources(user_id, agent_id)")

        # Memory items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_items (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at REAL NOT NULL,
                FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_user_agent ON memory_items(user_id, agent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_resource ON memory_items(resource_id)")

        # Categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                summary TEXT,
                created_at REAL NOT NULL,
                UNIQUE(user_id, agent_id, name)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_categories_user_agent ON categories(user_id, agent_id)")

        # Category-item relationships table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS category_items (
                item_id TEXT NOT NULL,
                category_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                PRIMARY KEY (item_id, category_id),
                FOREIGN KEY (item_id) REFERENCES memory_items(id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category_items_category ON category_items(category_id)")

        self.conn.commit()

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()

    # Resource operations
    def create_resource(self, resource: Resource) -> Resource:
        """Create a new resource."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO resources (id, user_id, agent_id, url, modality, local_path, caption, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resource.id,
                resource.user_id,
                resource.agent_id,
                resource.url,
                resource.modality,
                resource.local_path,
                resource.caption,
                resource.created_at or time.time(),
            ),
        )
        self.conn.commit()
        return resource

    def get_resource(self, resource_id: str, user_id: str, agent_id: str) -> Resource | None:
        """Get a resource by ID."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM resources WHERE id = ? AND user_id = ? AND agent_id = ?",
            (resource_id, user_id, agent_id),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Resource(
            id=row["id"],
            user_id=row["user_id"],
            agent_id=row["agent_id"],
            url=row["url"],
            modality=row["modality"],
            local_path=row["local_path"],
            caption=row["caption"],
            created_at=row["created_at"],
        )

    def list_resources(self, user_id: str, agent_id: str) -> list[Resource]:
        """List all resources for a user-agent pair."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM resources WHERE user_id = ? AND agent_id = ? ORDER BY created_at DESC",
            (user_id, agent_id),
        )
        return [
            Resource(
                id=row["id"],
                user_id=row["user_id"],
                agent_id=row["agent_id"],
                url=row["url"],
                modality=row["modality"],
                local_path=row["local_path"],
                caption=row["caption"],
                created_at=row["created_at"],
            )
            for row in cursor.fetchall()
        ]

    # Memory item operations
    def create_item(self, item: MemoryItem) -> MemoryItem:
        """Create a new memory item."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO memory_items (id, user_id, agent_id, resource_id, memory_type, summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.id,
                item.user_id,
                item.agent_id,
                item.resource_id,
                item.memory_type,
                item.summary,
                item.created_at or time.time(),
            ),
        )
        self.conn.commit()
        return item

    def get_item(self, item_id: str, user_id: str, agent_id: str) -> MemoryItem | None:
        """Get a memory item by ID."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM memory_items WHERE id = ? AND user_id = ? AND agent_id = ?",
            (item_id, user_id, agent_id),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return MemoryItem(
            id=row["id"],
            user_id=row["user_id"],
            agent_id=row["agent_id"],
            resource_id=row["resource_id"],
            memory_type=row["memory_type"],
            summary=row["summary"],
            embedding=[],  # Embeddings stored separately in vector DB
            created_at=row["created_at"],
        )

    def list_items(self, user_id: str, agent_id: str) -> list[MemoryItem]:
        """List all memory items for a user-agent pair."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM memory_items WHERE user_id = ? AND agent_id = ? ORDER BY created_at DESC",
            (user_id, agent_id),
        )
        return [
            MemoryItem(
                id=row["id"],
                user_id=row["user_id"],
                agent_id=row["agent_id"],
                resource_id=row["resource_id"],
                memory_type=row["memory_type"],
                summary=row["summary"],
                embedding=[],  # Embeddings stored separately in vector DB
                created_at=row["created_at"],
            )
            for row in cursor.fetchall()
        ]

    # Category operations
    def create_category(self, category: MemoryCategory) -> MemoryCategory:
        """Create a new category."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO categories (id, user_id, agent_id, name, description, summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                category.id,
                category.user_id,
                category.agent_id,
                category.name,
                category.description,
                category.summary,
                category.created_at or time.time(),
            ),
        )
        self.conn.commit()
        return category

    def get_category(self, category_id: str, user_id: str, agent_id: str) -> MemoryCategory | None:
        """Get a category by ID."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM categories WHERE id = ? AND user_id = ? AND agent_id = ?",
            (category_id, user_id, agent_id),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return MemoryCategory(
            id=row["id"],
            user_id=row["user_id"],
            agent_id=row["agent_id"],
            name=row["name"],
            description=row["description"],
            summary=row["summary"],
            created_at=row["created_at"],
        )

    def get_category_by_name(self, name: str, user_id: str, agent_id: str) -> MemoryCategory | None:
        """Get a category by name."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM categories WHERE name = ? AND user_id = ? AND agent_id = ?",
            (name, user_id, agent_id),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return MemoryCategory(
            id=row["id"],
            user_id=row["user_id"],
            agent_id=row["agent_id"],
            name=row["name"],
            description=row["description"],
            summary=row["summary"],
            created_at=row["created_at"],
        )

    def list_categories(self, user_id: str, agent_id: str) -> list[MemoryCategory]:
        """List all categories for a user-agent pair."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM categories WHERE user_id = ? AND agent_id = ? ORDER BY created_at DESC",
            (user_id, agent_id),
        )
        return [
            MemoryCategory(
                id=row["id"],
                user_id=row["user_id"],
                agent_id=row["agent_id"],
                name=row["name"],
                description=row["description"],
                summary=row["summary"],
                created_at=row["created_at"],
            )
            for row in cursor.fetchall()
        ]

    def update_category_summary(self, category_id: str, summary: str, user_id: str, agent_id: str) -> None:
        """Update category summary."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE categories SET summary = ? WHERE id = ? AND user_id = ? AND agent_id = ?",
            (summary, category_id, user_id, agent_id),
        )
        self.conn.commit()

    # Category-item relationship operations
    def create_category_item(self, rel: CategoryItem) -> CategoryItem:
        """Create a category-item relationship."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO category_items (item_id, category_id, user_id, agent_id)
            VALUES (?, ?, ?, ?)
            """,
            (rel.item_id, rel.category_id, rel.user_id, rel.agent_id),
        )
        self.conn.commit()
        return rel

    def list_category_items(self, user_id: str, agent_id: str) -> list[CategoryItem]:
        """List all category-item relationships for a user-agent pair."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM category_items WHERE user_id = ? AND agent_id = ?",
            (user_id, agent_id),
        )
        return [
            CategoryItem(
                item_id=row["item_id"],
                category_id=row["category_id"],
                user_id=row["user_id"],
                agent_id=row["agent_id"],
            )
            for row in cursor.fetchall()
        ]

    def get_items_by_category(self, category_id: str, user_id: str, agent_id: str) -> list[str]:
        """Get all item IDs for a category."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT item_id FROM category_items WHERE category_id = ? AND user_id = ? AND agent_id = ?",
            (category_id, user_id, agent_id),
        )
        return [row["item_id"] for row in cursor.fetchall()]
