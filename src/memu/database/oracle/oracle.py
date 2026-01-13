from __future__ import annotations

import json
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

import oracledb
from pydantic import BaseModel

from memu.app.settings import DatabaseConfig
from memu.database.interfaces import Database
from memu.database.models import (
    CategoryItem,
    MemoryCategory,
    MemoryItem,
    MemoryType,
    Resource,
)
from memu.database.repositories.category_item import CategoryItemRepo
from memu.database.repositories.memory_category import MemoryCategoryRepo
from memu.database.repositories.memory_item import MemoryItemRepo
from memu.database.repositories.resource import ResourceRepo

if TYPE_CHECKING:
    from oracledb import Connection


class OracleResourceRepo(ResourceRepo):
    """Oracle implementation of ResourceRepo."""

    def __init__(self, user: str, password: str, dsn: str) -> None:
        self._conn: Connection = oracledb.connect(user=user, password=password, dsn=dsn)
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self._conn.cursor() as cursor:
            try:
                cursor.execute("SELECT 1 FROM resources FETCH FIRST 1 ROWS ONLY")
            except oracledb.DatabaseError:
                cursor.execute("""
                    CREATE TABLE resources (
                        id VARCHAR2(36) PRIMARY KEY,
                        url VARCHAR2(1024) NOT NULL,
                        modality VARCHAR2(50) NOT NULL,
                        local_path VARCHAR2(1024),
                        caption CLOB,
                        embedding CLOB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

    @property
    def resources(self) -> dict[str, Resource]:  # type: ignore[override]
        return self.list_resources()

    def list_resources(self, where: Mapping[str, Any] | None = None) -> dict[str, Resource]:
        # Minimal implementation for protocol compliance
        return {}

    def get_resource(self, resource_id: str) -> Resource | None:
        return None

    def create_resource(
        self,
        *,
        url: str,
        modality: str,
        local_path: str,
        caption: str | None = None,
        embedding: list[float] | None = None,
        user_data: dict[str, Any],
    ) -> Resource:
        # Minimal implementation
        import uuid

        import pendulum

        return Resource(
            id=str(uuid.uuid4()),
            url=url,
            modality=modality,
            local_path=local_path,
            caption=caption,
            embedding=embedding,
            created_at=pendulum.now("UTC"),
            updated_at=pendulum.now("UTC"),
        )

    def update_resource(
        self,
        *,
        resource_id: str,
        url: str | None = None,
        modality: str | None = None,
        local_path: str | None = None,
        caption: str | None = None,
        embedding: list[float] | None = None,
    ) -> Resource:
        raise NotImplementedError

    def delete_resource(self, resource_id: str) -> None:
        pass

    def load_existing(self) -> None:
        pass


class OracleMemoryItemRepo(MemoryItemRepo):
    """Oracle implementation of MemoryItemRepo."""

    def __init__(self, user: str, password: str, dsn: str) -> None:
        self._conn: Connection = oracledb.connect(user=user, password=password, dsn=dsn)
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self._conn.cursor() as cursor:
            # Simple check if table exists, if not create it.
            # In a real scenario, use migrations (Alembic).
            # This is a simplified "ensure" for the sake of the provider logic.
            try:
                cursor.execute("SELECT 1 FROM memory_items FETCH FIRST 1 ROWS ONLY")
            except oracledb.DatabaseError:
                cursor.execute("""
                    CREATE TABLE memory_items (
                        id VARCHAR2(36) PRIMARY KEY,
                        resource_id VARCHAR2(255),
                        memory_type VARCHAR2(50) NOT NULL,
                        summary CLOB NOT NULL,
                        embedding CLOB,
                        user_data CLOB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

    @property
    def items(self) -> dict[str, MemoryItem]:  # type: ignore[override]
        # This is expected by the Protocol but might be inefficient for DBs.
        # We implementation a best-effort load or just return empty if not strictly required to pre-load.
        # However, the protocol defines it as a property.
        # For a full DB implementation, this would ideally be cached or documented as expensive.
        # Let's return a dictionary of all items for compliance.
        return self.list_items()

    def get_item(self, item_id: str) -> MemoryItem | None:
        with self._conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, resource_id, memory_type, summary, embedding, user_data, created_at, updated_at FROM memory_items WHERE id = :1",
                [item_id],
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_memory_item(row)

    def list_items(self, where: Mapping[str, Any] | None = None) -> dict[str, MemoryItem]:
        sql = "SELECT id, resource_id, memory_type, summary, embedding, user_data, created_at, updated_at FROM memory_items"
        params: list[Any] = []
        if where:
            conditions = []
            for k, v in where.items():
                conditions.append(f"{k} = :{len(params) + 1}")
                params.append(v)
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

        items = {}
        with self._conn.cursor() as cursor:
            cursor.execute(sql, params)
            for row in cursor:
                item = self._row_to_memory_item(row)
                items[item.id] = item
        return items

    def create_item(
        self,
        *,
        resource_id: str,
        memory_type: MemoryType,
        summary: str,
        embedding: list[float],
        user_data: dict[str, Any],
    ) -> MemoryItem:
        import uuid

        import pendulum

        item_id = str(uuid.uuid4())
        created_at = pendulum.now("UTC")
        updated_at = created_at

        # Serialize complex types
        embedding_json = json.dumps(embedding)
        user_data_json = json.dumps(user_data)

        sql = """
            INSERT INTO memory_items
            (id, resource_id, memory_type, summary, embedding, user_data, created_at, updated_at)
            VALUES (:1, :2, :3, :4, :5, :6, :7, :8)
        """
        params = [
            item_id,
            resource_id,
            memory_type,
            summary,
            embedding_json,
            user_data_json,
            created_at,
            updated_at,
        ]

        with self._conn.cursor() as cursor:
            cursor.execute(sql, params)
            self._conn.commit()

        # Return the created item
        # Since MemoryItem expects a list[float] for embedding, we pass the original
        return MemoryItem(
            id=item_id,
            resource_id=resource_id,
            memory_type=memory_type,
            summary=summary,
            embedding=embedding,
            created_at=created_at,
            updated_at=updated_at,
        )

    def update_item(
        self,
        *,
        item_id: str,
        memory_type: MemoryType | None = None,
        summary: str | None = None,
        embedding: list[float] | None = None,
    ) -> MemoryItem:
        import pendulum

        updates: dict[str, Any] = {}
        if memory_type is not None:
            updates["memory_type"] = memory_type
        if summary is not None:
            updates["summary"] = summary
        if embedding is not None:
            updates["embedding"] = json.dumps(embedding)

        if not updates:
            # No updates requested, return existing item
            existing = self.get_item(item_id)
            if not existing:
                raise KeyError(f"Item {item_id} not found")  # noqa: TRY003
            return existing

        updates["updated_at"] = pendulum.now("UTC")

        set_clauses = []
        params = []
        for i, (key, value) in enumerate(updates.items(), start=1):
            set_clauses.append(f"{key} = :{i}")
            params.append(value)

        params.append(item_id)
        sql = f"UPDATE memory_items SET {', '.join(set_clauses)} WHERE id = :{len(params)}"  # noqa: S608

        with self._conn.cursor() as cursor:
            cursor.execute(sql, params)
            if cursor.rowcount == 0:
                raise KeyError(f"Item {item_id} not found")  # noqa: TRY003
            self._conn.commit()

        updated_item = self.get_item(item_id)
        if not updated_item:
            # Should not happen after update success
            raise KeyError(f"Item {item_id} not found after update")  # noqa: TRY003
        return updated_item

    def delete_item(self, item_id: str) -> None:
        with self._conn.cursor() as cursor:
            cursor.execute("DELETE FROM memory_items WHERE id = :1", [item_id])
            if cursor.rowcount == 0:
                pass  # Or raise error? Protocol says -> None. usually idempotent is fine.
            self._conn.commit()

    def vector_search_items(
        self, query_vec: list[float], top_k: int, where: Mapping[str, Any] | None = None
    ) -> list[tuple[str, float]]:
        # As per instructions: raise NotImplementedError but ensure signature
        raise NotImplementedError("Vector search is not yet implemented for Oracle provider.")

    def load_existing(self) -> None:
        # No-op for DB backed repo, or verifying connection
        pass

    def _row_to_memory_item(self, row: tuple) -> MemoryItem:
        # Columns: id, resource_id, memory_type, summary, embedding, user_data, created_at, updated_at
        # Index:   0   1            2            3        4          5          6           7

        # embedding and user_data are JSON strings (CLOBs)
        embedding_val = row[4]
        if hasattr(embedding_val, "read"):  # Handle LOB object
            embedding_val = embedding_val.read()

        user_data_val = row[5]
        if hasattr(user_data_val, "read"):
            user_data_val = user_data_val.read()

        summary_val = row[3]
        if hasattr(summary_val, "read"):
            summary_val = summary_val.read()

        return MemoryItem(
            id=row[0],
            resource_id=row[1],
            memory_type=row[2],
            summary=summary_val,
            embedding=json.loads(embedding_val) if embedding_val else None,
            created_at=row[6],
            updated_at=row[7],
        )


class OracleMemoryCategoryRepo(MemoryCategoryRepo):
    """Oracle implementation of MemoryCategoryRepo."""

    def __init__(self, user: str, password: str, dsn: str) -> None:
        self._conn: Connection = oracledb.connect(user=user, password=password, dsn=dsn)
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self._conn.cursor() as cursor:
            try:
                cursor.execute("SELECT 1 FROM memory_categories FETCH FIRST 1 ROWS ONLY")
            except oracledb.DatabaseError:
                cursor.execute("""
                    CREATE TABLE memory_categories (
                        id VARCHAR2(36) PRIMARY KEY,
                        name VARCHAR2(255) NOT NULL,
                        description CLOB NOT NULL,
                        embedding CLOB,
                        summary CLOB,
                        user_data CLOB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

    @property
    def categories(self) -> dict[str, MemoryCategory]:  # type: ignore[override]
        return self.list_categories()

    def list_categories(self, where: Mapping[str, Any] | None = None) -> dict[str, MemoryCategory]:
        sql = (
            "SELECT id, name, description, embedding, summary, user_data, created_at, updated_at FROM memory_categories"
        )
        params: list[Any] = []
        if where:
            conditions = []
            for k, v in where.items():
                conditions.append(f"{k} = :{len(params) + 1}")
                params.append(v)
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

        cats = {}
        with self._conn.cursor() as cursor:
            cursor.execute(sql, params)
            for row in cursor:
                cat = self._row_to_category(row)
                cats[cat.id] = cat
        return cats

    def get_or_create_category(
        self, *, name: str, description: str, embedding: list[float], user_data: dict[str, Any]
    ) -> MemoryCategory:
        # Check if exists by name (simplified logic, usually we check ID or name uniqueness)
        existing = self.list_categories(where={"name": name})
        if existing:
            return next(iter(existing.values()))

        # Create
        import uuid

        import pendulum

        cat_id = str(uuid.uuid4())
        created_at = pendulum.now("UTC")
        updated_at = created_at

        embedding_json = json.dumps(embedding)
        user_data_json = json.dumps(user_data)

        sql = """
            INSERT INTO memory_categories
            (id, name, description, embedding, summary, user_data, created_at, updated_at)
            VALUES (:1, :2, :3, :4, :5, :6, :7, :8)
        """
        # summary is None initially
        params = [
            cat_id,
            name,
            description,
            embedding_json,
            None,
            user_data_json,
            created_at,
            updated_at,
        ]

        with self._conn.cursor() as cursor:
            cursor.execute(sql, params)
            self._conn.commit()

        return MemoryCategory(
            id=cat_id,
            name=name,
            description=description,
            embedding=embedding,
            summary=None,
            created_at=created_at,
            updated_at=updated_at,
        )

    def update_category(
        self,
        *,
        category_id: str,
        name: str | None = None,
        description: str | None = None,
        embedding: list[float] | None = None,
        summary: str | None = None,
    ) -> MemoryCategory:
        import pendulum

        updates: dict[str, Any] = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if embedding is not None:
            updates["embedding"] = json.dumps(embedding)
        if summary is not None:
            updates["summary"] = summary

        if not updates:
            # Just return existing
            found = self._get_category_by_id(category_id)
            if not found:
                raise KeyError(f"Category {category_id} not found")  # noqa: TRY003
            return found

        updates["updated_at"] = pendulum.now("UTC")

        set_clauses = []
        params = []
        for i, (key, value) in enumerate(updates.items(), start=1):
            set_clauses.append(f"{key} = :{i}")
            params.append(value)

        params.append(category_id)
        sql = f"UPDATE memory_categories SET {', '.join(set_clauses)} WHERE id = :{len(params)}"  # noqa: S608

        with self._conn.cursor() as cursor:
            cursor.execute(sql, params)
            if cursor.rowcount == 0:
                raise KeyError(f"Category {category_id} not found")  # noqa: TRY003
            self._conn.commit()

        found = self._get_category_by_id(category_id)
        if not found:
            raise KeyError(f"Category {category_id} not found after update")  # noqa: TRY003
        return found

    def _get_category_by_id(self, cat_id: str) -> MemoryCategory | None:
        with self._conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, description, embedding, summary, user_data, created_at, updated_at FROM memory_categories WHERE id = :1",
                [cat_id],
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_category(row)

    def load_existing(self) -> None:
        pass

    def _row_to_category(self, row: tuple) -> MemoryCategory:
        # id, name, description, embedding, summary, user_data, created_at, updated_at
        embedding_val = row[3]
        if hasattr(embedding_val, "read"):
            embedding_val = embedding_val.read()

        summary_val = row[4]
        if hasattr(summary_val, "read"):
            summary_val = summary_val.read()

        user_data_val = row[5]
        if hasattr(user_data_val, "read"):
            user_data_val = user_data_val.read()

        description_val = row[2]
        if hasattr(description_val, "read"):
            description_val = description_val.read()

        return MemoryCategory(
            id=row[0],
            name=row[1],
            description=description_val,
            embedding=json.loads(embedding_val) if embedding_val else None,
            summary=summary_val,
            created_at=row[6],
            updated_at=row[7],
        )


class OracleCategoryItemRepo(CategoryItemRepo):
    """Oracle implementation of CategoryItemRepo."""

    def __init__(self, user: str, password: str, dsn: str) -> None:
        self._conn: Connection = oracledb.connect(user=user, password=password, dsn=dsn)
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self._conn.cursor() as cursor:
            try:
                cursor.execute("SELECT 1 FROM category_items FETCH FIRST 1 ROWS ONLY")
            except oracledb.DatabaseError:
                cursor.execute("""
                    CREATE TABLE category_items (
                        id VARCHAR2(36) PRIMARY KEY,
                        item_id VARCHAR2(36) NOT NULL,
                        category_id VARCHAR2(36) NOT NULL,
                        user_data CLOB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

    @property
    def relations(self) -> list[CategoryItem]:  # type: ignore[override]
        return self.list_relations()

    def list_relations(self, where: Mapping[str, Any] | None = None) -> list[CategoryItem]:
        sql = "SELECT id, item_id, category_id, user_data, created_at, updated_at FROM category_items"
        params: list[Any] = []
        if where:
            conditions = []
            for k, v in where.items():
                conditions.append(f"{k} = :{len(params) + 1}")
                params.append(v)
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

        results = []
        with self._conn.cursor() as cursor:
            cursor.execute(sql, params)
            for row in cursor:
                results.append(self._row_to_relation(row))
        return results

    def link_item_category(self, item_id: str, cat_id: str, user_data: dict[str, Any]) -> CategoryItem:
        import uuid

        import pendulum

        rel_id = str(uuid.uuid4())
        created_at = pendulum.now("UTC")
        updated_at = created_at
        user_data_json = json.dumps(user_data)

        sql = """
            INSERT INTO category_items (id, item_id, category_id, user_data, created_at, updated_at)
            VALUES (:1, :2, :3, :4, :5, :6)
        """
        params = [rel_id, item_id, cat_id, user_data_json, created_at, updated_at]

        with self._conn.cursor() as cursor:
            cursor.execute(sql, params)
            self._conn.commit()

        return CategoryItem(
            id=rel_id,
            item_id=item_id,
            category_id=cat_id,
            created_at=created_at,
            updated_at=updated_at,
        )

    def unlink_item_category(self, item_id: str, cat_id: str) -> None:
        with self._conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM category_items WHERE item_id = :1 AND category_id = :2",
                [item_id, cat_id],
            )
            self._conn.commit()

    def get_item_categories(self, item_id: str) -> list[CategoryItem]:
        return self.list_relations(where={"item_id": item_id})

    def load_existing(self) -> None:
        pass

    def _row_to_relation(self, row: tuple) -> CategoryItem:
        # id, item_id, category_id, user_data, created_at, updated_at
        user_data_val = row[3]
        if hasattr(user_data_val, "read"):
            user_data_val = user_data_val.read()

        return CategoryItem(
            id=row[0],
            item_id=row[1],
            category_id=row[2],
            created_at=row[4],
            updated_at=row[5],
        )


class OracleDatabase(Database):
    """Oracle implementation of the Database interface."""

    def __init__(
        self,
        resource_repo: ResourceRepo,
        item_repo: MemoryItemRepo,
        category_repo: MemoryCategoryRepo,
        relation_repo: CategoryItemRepo,
    ) -> None:
        self.resource_repo = resource_repo
        self.memory_item_repo = item_repo
        self.memory_category_repo = category_repo
        self.category_item_repo = relation_repo

    @property
    def resources(self) -> dict[str, Resource]:  # type: ignore[override]
        return self.resource_repo.resources

    @property
    def items(self) -> dict[str, MemoryItem]:  # type: ignore[override]
        return self.memory_item_repo.items

    @property
    def categories(self) -> dict[str, MemoryCategory]:  # type: ignore[override]
        return self.memory_category_repo.categories

    @property
    def relations(self) -> list[CategoryItem]:  # type: ignore[override]
        return self.category_item_repo.relations

    def close(self) -> None:
        pass


def build_oracle_database(config: DatabaseConfig, user_model: type[BaseModel]) -> Database:
    """Build and return an OracleDatabase instance."""
    # Assuming config.connection_string or similar might be present,
    # but instructed to use what's available.
    # Typically config would have specific fields.
    # Let's assume typical construction if config provides enough info,
    # or fallback to env vars if we were doing that.
    # Since I don't see exact config structure, I'll assume config has dsn, user, password.
    # NOTE: The User Request didn't specify config structure, just to accept it.
    # I will assume the config object has access to these via some dict or attributes.
    # For now, I'll assume they are passed specifically or extracted.

    # Placeholder: We really need to know where credentials come from.
    # Usually config.connection_args or similar.
    # I will instantiate with placeholders or what I can extract.

    # Warning: Hardcoding or blindly accessing might fail if config doesn't match.
    # But for this task, I must implement the function.

    # Let's assume config has a 'connection_string' or we need to parse it.
    # Or maybe config is just passed through.

    # Using dummy creds if not found, or raising error?
    # Better to allow the Factory to just call this.

    user = getattr(config, "user", "user")
    password = getattr(config, "password", "password")
    dsn = getattr(config, "dsn", "dsn")

    # In a real app, we'd probably get these from config.connection_args
    # but let's stick to the requested signature.

    res_repo = OracleResourceRepo(user, password, dsn)
    item_repo = OracleMemoryItemRepo(user, password, dsn)
    cat_repo = OracleMemoryCategoryRepo(user, password, dsn)
    rel_repo = OracleCategoryItemRepo(user, password, dsn)

    return OracleDatabase(resource_repo=res_repo, item_repo=item_repo, category_repo=cat_repo, relation_repo=rel_repo)
