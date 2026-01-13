from __future__ import annotations

import contextlib
import logging
from collections.abc import Mapping
from typing import Any, Literal

with contextlib.suppress(ImportError):
    pass

from sqlalchemy import JSON
from sqlmodel import Field, SQLModel, select

from memu.database.interfaces import (
    CategoryItemRepo,
    Database,
    MemoryCategoryRepo,
    MemoryItemRepo,
    ResourceRepo,
)
from memu.database.models import (
    CategoryItem,
    MemoryCategory,
    MemoryItem,
    Resource,
)
from memu.database.mssql.session import SessionManager

logger = logging.getLogger(__name__)

# --- EXPLICIT MODELS ---


class MssqlResourceModel(SQLModel, Resource, table=True):
    """SQLModel representation of a Resource for MSSQL."""

    model_config = {"arbitrary_types_allowed": True}
    __tablename__ = "resources"
    embedding: list[float] | None = Field(default=None, sa_type=JSON)


class MssqlMemoryItemModel(SQLModel, MemoryItem, table=True):
    """SQLModel representation of a MemoryItem for MSSQL."""

    model_config = {"arbitrary_types_allowed": True}
    __tablename__ = "memory_items"
    embedding: list[float] | None = Field(default=None, sa_type=JSON)


class MssqlMemoryCategoryModel(SQLModel, MemoryCategory, table=True):
    """SQLModel representation of a MemoryCategory for MSSQL."""

    model_config = {"arbitrary_types_allowed": True}
    __tablename__ = "memory_categories"
    embedding: list[float] | None = Field(default=None, sa_type=JSON)


class MssqlCategoryItemModel(SQLModel, CategoryItem, table=True):
    """SQLModel representation of a CategoryItem for MSSQL."""

    model_config = {"arbitrary_types_allowed": True}
    __tablename__ = "category_items"


# --- REPOSITORIES ---


class MssqlResourceRepo(ResourceRepo):
    """MSSQL implementation of the ResourceRepo."""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.resources: dict[str, Resource] = {}

    def load_existing(self) -> None:
        return None

    def create_resource(
        self,
        *,
        url: str | None = None,
        modality: str = "text",
        local_path: str | None = None,
        caption: str | None = None,
        embedding: list[float] | None = None,
        user_data: dict[str, Any] | None = None,
    ) -> Resource:
        db_obj = MssqlResourceModel(
            url=url or "",
            modality=modality,
            local_path=local_path or "",
            caption=caption,
            embedding=embedding,
            user_data=user_data or {},
        )
        with self.session_manager.session() as session:
            session.add(db_obj)
            session.commit()
            session.refresh(db_obj)
            return db_obj

    def get_resource(self, resource_id: str) -> Resource | None:
        with self.session_manager.session() as session:
            return session.get(MssqlResourceModel, resource_id)

    def delete_resource(self, resource_id: str) -> None:
        with self.session_manager.session() as session:
            db_obj = session.get(MssqlResourceModel, resource_id)
            if db_obj:
                session.delete(db_obj)
                session.commit()

    def list_resources(self, where: Mapping[str, Any] | None = None) -> dict[str, Resource]:
        with self.session_manager.session() as session:
            statement = select(MssqlResourceModel)

            results = session.exec(statement).all()
            return {res.id: res for res in results}


class MssqlMemoryCategoryRepo(MemoryCategoryRepo):
    """MSSQL implementation of the MemoryCategoryRepo."""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.categories: dict[str, MemoryCategory] = {}

    def load_existing(self) -> None:
        return None

    def get_or_create_category(
        self, *, name: str, description: str, embedding: list[float], user_data: dict[str, Any]
    ) -> MemoryCategory:
        with self.session_manager.session() as session:
            statement = select(MssqlMemoryCategoryModel).where(MssqlMemoryCategoryModel.name == name)
            existing = session.exec(statement).first()
            if existing:
                return existing

            new_cat = MssqlMemoryCategoryModel(
                name=name,
                description=description,
                embedding=embedding,
            )
            session.add(new_cat)
            session.commit()
            session.refresh(new_cat)
            return new_cat

    def update_category(
        self,
        *,
        category_id: str,
        name: str | None = None,
        description: str | None = None,
        embedding: list[float] | None = None,
        summary: str | None = None,
    ) -> MemoryCategory:
        with self.session_manager.session() as session:
            db_obj = session.get(MssqlMemoryCategoryModel, category_id)
            if not db_obj:
                msg = f"Category with ID {category_id} not found"
                raise ValueError(msg)

            if name is not None:
                db_obj.name = name
            if description is not None:
                db_obj.description = description
            if embedding is not None:
                db_obj.embedding = embedding
            if summary is not None:
                db_obj.summary = summary

            session.add(db_obj)
            session.commit()
            session.refresh(db_obj)
            return db_obj

    def delete_category(self, category_id: str) -> None:
        with self.session_manager.session() as session:
            db_obj = session.get(MssqlMemoryCategoryModel, category_id)
            if db_obj:
                session.delete(db_obj)
                session.commit()

    def list_categories(self, where: Mapping[str, Any] | None = None) -> dict[str, MemoryCategory]:
        with self.session_manager.session() as session:
            statement = select(MssqlMemoryCategoryModel)
            results = session.exec(statement).all()
            return {cat.id: cat for cat in results}


class MssqlMemoryItemRepo(MemoryItemRepo):
    """MSSQL implementation of the MemoryItemRepo."""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.items: dict[str, MemoryItem] = {}

    def load_existing(self) -> None:
        return None

    def create_item(
        self,
        *,
        resource_id: str,
        memory_type: Literal["profile", "event", "knowledge", "behavior", "skill"],
        summary: str,
        embedding: list[float],
        user_data: dict[str, Any],
    ) -> MemoryItem:
        db_obj = MssqlMemoryItemModel(
            resource_id=resource_id,
            memory_type=memory_type,
            summary=summary,
            embedding=embedding,
        )
        with self.session_manager.session() as session:
            session.add(db_obj)
            session.commit()
            session.refresh(db_obj)
            return db_obj

    def get_item(self, item_id: str) -> MemoryItem | None:
        with self.session_manager.session() as session:
            return session.get(MssqlMemoryItemModel, item_id)

    def update_item(
        self,
        *,
        item_id: str,
        memory_type: Literal["profile", "event", "knowledge", "behavior", "skill"] | None = None,
        summary: str | None = None,
        embedding: list[float] | None = None,
    ) -> MemoryItem:
        with self.session_manager.session() as session:
            db_obj = session.get(MssqlMemoryItemModel, item_id)
            if not db_obj:
                msg = f"Item with ID {item_id} not found"
                raise ValueError(msg)

            if memory_type is not None:
                db_obj.memory_type = memory_type
            if summary is not None:
                db_obj.summary = summary
            if embedding is not None:
                db_obj.embedding = embedding

            session.add(db_obj)
            session.commit()
            session.refresh(db_obj)
            return db_obj

    def delete_item(self, item_id: str) -> None:
        with self.session_manager.session() as session:
            db_obj = session.get(MssqlMemoryItemModel, item_id)
            if db_obj:
                session.delete(db_obj)
                session.commit()

    def list_items(self, where: Mapping[str, Any] | None = None) -> dict[str, MemoryItem]:
        with self.session_manager.session() as session:
            statement = select(MssqlMemoryItemModel)
            results = session.exec(statement).all()
            return {item.id: item for item in results}

    def vector_search_items(
        self, query_vec: list[float], top_k: int, where: Mapping[str, Any] | None = None
    ) -> list[tuple[str, float]]:
        return []


class MssqlCategoryItemRepo(CategoryItemRepo):
    """MSSQL implementation of the CategoryItemRepo."""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.relations: list[CategoryItem] = []

    def load_existing(self) -> None:
        return None

    def link_item_category(self, item_id: str, cat_id: str, user_data: dict[str, Any]) -> CategoryItem:
        with self.session_manager.session() as session:
            statement = select(MssqlCategoryItemModel).where(
                MssqlCategoryItemModel.item_id == item_id, MssqlCategoryItemModel.category_id == cat_id
            )
            existing = session.exec(statement).first()
            if existing:
                return existing

            new_relation = MssqlCategoryItemModel(item_id=item_id, category_id=cat_id)
            session.add(new_relation)
            session.commit()
            session.refresh(new_relation)
            return new_relation

    def unlink_item_category(self, item_id: str, cat_id: str) -> None:
        with self.session_manager.session() as session:
            statement = select(MssqlCategoryItemModel).where(
                MssqlCategoryItemModel.item_id == item_id, MssqlCategoryItemModel.category_id == cat_id
            )
            results = session.exec(statement).all()
            for obj in results:
                session.delete(obj)
            if results:
                session.commit()

    def get_item_categories(self, item_id: str) -> list[CategoryItem]:
        with self.session_manager.session() as session:
            statement = select(MssqlCategoryItemModel).where(MssqlCategoryItemModel.item_id == item_id)
            return list(session.exec(statement).all())

    def list_relations(self, where: Mapping[str, Any] | None = None) -> list[CategoryItem]:
        with self.session_manager.session() as session:
            statement = select(MssqlCategoryItemModel)
            return list(session.exec(statement).all())


class MssqlStore(Database):
    """MSSQL Database implementation."""

    def __init__(self, dsn: str):
        self.session_manager = SessionManager(dsn=dsn)

        self.resource_repo = MssqlResourceRepo(self.session_manager)
        self.memory_category_repo = MssqlMemoryCategoryRepo(self.session_manager)
        self.memory_item_repo = MssqlMemoryItemRepo(self.session_manager)
        self.category_item_repo = MssqlCategoryItemRepo(self.session_manager)

        self._init_db()

    def _init_db(self) -> None:
        SQLModel.metadata.create_all(self.session_manager._engine)

    def close(self) -> None:
        self.session_manager.close()
