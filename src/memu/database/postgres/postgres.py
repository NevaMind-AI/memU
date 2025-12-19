from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any

from memu.database.inmemory.repo import InMemoryStore
from memu.database.postgres.schema import Vector, get_sqlalchemy_models, require_sqlalchemy

logger = logging.getLogger(__name__)

try:  # Optional dependency for Postgres backend
    from alembic import command
    from alembic.config import Config as AlembicConfig
except ImportError as exc:  # pragma: no cover - optional dependency
    command = None
    AlembicConfig = None
    _alembic_import_error = exc
else:
    _alembic_import_error = None

try:  # Optional dependency for Postgres backend
    from sqlmodel import Session, create_engine, select
except ImportError as exc:  # pragma: no cover - optional dependency
    Session = None
    create_engine = None
    select = None
    _sqlmodel_import_error_pg = exc
else:
    _sqlmodel_import_error_pg = None


class PostgresStore(InMemoryStore):
    def __init__(
        self,
        *,
        dsn: str,
        scope_key: str,
        ddl_mode: str = "create",  # kept for API compatibility
        vector_provider: str | None = None,
        base_model: type | None = None,
        resource_model: type | None = None,
        memory_item_model: type | None = None,
        memory_category_model: type | None = None,
        category_item_model: type | None = None,
    ) -> None:
        require_sqlalchemy()
        if command is None or AlembicConfig is None or create_engine is None or select is None or Session is None:
            msg = "sqlmodel, sqlalchemy, and alembic are required for PostgresStore"
            raise ImportError(msg) from (_alembic_import_error or _sqlmodel_import_error_pg)
        self.dsn = dsn
        self.ddl_mode = ddl_mode
        self.vector_provider = vector_provider
        self._use_vector_type = vector_provider == "pgvector"
        if self._use_vector_type and Vector is None:
            msg = "pgvector is required when vector_provider='pgvector'"
            raise ImportError(msg)

        self._engine = create_engine(self.dsn, pool_pre_ping=True)
        self._models = get_sqlalchemy_models(self._use_vector_type)
        self._run_migrations()

        super().__init__(
            scope_key=scope_key,
            base_model=base_model,
            resource_model=resource_model,
            memory_item_model=memory_item_model,
            memory_category_model=memory_category_model,
            category_item_model=category_item_model,
        )
        self._load_existing()

    def _session(self) -> Session:
        return Session(self._engine, expire_on_commit=False)

    def close(self) -> None:
        try:
            self._engine.dispose()
        except Exception:
            logger.exception("Failed to close Postgres engine")

    def _alembic_config(self) -> AlembicConfig:
        cfg = AlembicConfig()
        cfg.set_main_option("script_location", str(Path(__file__).with_name("migrations")))
        cfg.set_main_option("sqlalchemy.url", self.dsn)
        cfg.attributes["use_vector"] = self._use_vector_type
        return cfg

    def _run_migrations(self) -> None:
        cfg = self._alembic_config()
        command.upgrade(cfg, "head")

    def _load_existing(self) -> None:
        with self._session() as session:
            resources = session.scalars(
                select(self._models.Resource).where(self._models.Resource.scope_key == self.scope_key)
            ).all()
            for row in resources:
                res = self.resource_model(
                    id=row.id,
                    url=row.url,
                    modality=row.modality,
                    local_path=row.local_path,
                    caption=row.caption,
                    embedding=self._normalize_embedding(row.embedding),
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                self.resources[row.id] = res

            categories = session.scalars(
                select(self._models.MemoryCategory).where(self._models.MemoryCategory.scope_key == self.scope_key)
            ).all()
            for row in categories:
                cat = self.memory_category_model(
                    id=row.id,
                    name=row.name,
                    description=row.description or "",
                    embedding=self._normalize_embedding(row.embedding),
                    summary=row.summary,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                self.categories[row.id] = cat

            items = session.scalars(
                select(self._models.MemoryItem).where(self._models.MemoryItem.scope_key == self.scope_key)
            ).all()
            for row in items:
                item = self.memory_item_model(
                    id=row.id,
                    resource_id=row.resource_id,
                    memory_type=row.memory_type,
                    summary=row.summary,
                    embedding=self._normalize_embedding(row.embedding),
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                self.items[row.id] = item

            relations = session.scalars(
                select(self._models.CategoryItem).where(self._models.CategoryItem.scope_key == self.scope_key)
            ).all()
            for row in relations:
                rel = self.category_item_model(
                    id=row.id,
                    item_id=row.item_id,
                    category_id=row.category_id,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                self.relations.append(rel)

    def _normalize_embedding(self, embedding: Any) -> list[float] | None:
        if embedding is None:
            return None
        if hasattr(embedding, "to_list"):
            try:
                return [float(x) for x in embedding.to_list()]
            except Exception:
                logger.debug("Could not convert pgvector value %s", embedding)
                return None
        if isinstance(embedding, str):
            stripped = embedding.strip("[]")
            if not stripped:
                return []
            return [float(x) for x in stripped.split(",")]
        try:
            return [float(x) for x in embedding]
        except Exception:
            logger.debug("Could not normalize embedding %s", embedding)
            return None

    def _prepare_embedding(self, embedding: list[float] | None) -> Any:
        if embedding is None:
            return None
        return embedding

    def _merge_and_commit(self, session: Session, obj: Any) -> None:
        session.merge(obj)
        session.commit()

    def create_resource(self, *, url: str, modality: str, local_path: str) -> Any:
        res = super().create_resource(url=url, modality=modality, local_path=local_path)
        now = time.time()
        record = self._models.Resource(
            id=res.id,
            scope_key=self.scope_key,
            url=res.url,
            modality=res.modality,
            local_path=res.local_path,
            caption=res.caption,
            embedding=self._prepare_embedding(res.embedding),
            created_at=now,
            updated_at=now,
        )
        with self._session() as session:
            self._merge_and_commit(session, record)
        return res

    def get_or_create_category(self, *, name: str, description: str, embedding: list[float]) -> Any:
        for c in self.categories.values():
            if c.name == name:
                if not c.embedding:
                    c.embedding = embedding
                    c.updated_at = time.time()
                if not c.description:
                    c.description = description
                    c.updated_at = time.time()
                self._upsert_category(c)
                return c
        cid = str(uuid.uuid4())
        cat = self.memory_category_model(id=cid, name=name, description=description, embedding=embedding)
        self.categories[cid] = cat
        self._upsert_category(cat)
        return cat

    def _upsert_category(self, cat: Any) -> None:
        now = time.time()
        record = self._models.MemoryCategory(
            id=cat.id,
            scope_key=self.scope_key,
            name=cat.name,
            description=getattr(cat, "description", None),
            embedding=self._prepare_embedding(getattr(cat, "embedding", None)),
            summary=getattr(cat, "summary", None),
            created_at=getattr(cat, "created_at", now),
            updated_at=getattr(cat, "updated_at", now),
        )
        with self._session() as session:
            self._merge_and_commit(session, record)

    def create_item(self, *, resource_id: str, memory_type: str, summary: str, embedding: list[float]) -> Any:
        item = super().create_item(
            resource_id=resource_id,
            memory_type=memory_type,
            summary=summary,
            embedding=embedding,
        )
        now = time.time()
        record = self._models.MemoryItem(
            id=item.id,
            scope_key=self.scope_key,
            resource_id=resource_id,
            memory_type=memory_type,
            summary=summary,
            embedding=self._prepare_embedding(embedding),
            created_at=now,
            updated_at=now,
        )
        with self._session() as session:
            self._merge_and_commit(session, record)
        return item

    def link_item_category(self, item_id: str, cat_id: str) -> Any:
        rel = super().link_item_category(item_id=item_id, cat_id=cat_id)
        now = time.time()
        record = self._models.CategoryItem(
            id=rel.id,
            scope_key=self.scope_key,
            item_id=item_id,
            category_id=cat_id,
            created_at=getattr(rel, "created_at", now),
            updated_at=getattr(rel, "updated_at", now),
        )
        with self._session() as session:
            existing = session.scalar(
                select(self._models.CategoryItem.id).where(
                    self._models.CategoryItem.scope_key == self.scope_key,
                    self._models.CategoryItem.item_id == item_id,
                    self._models.CategoryItem.category_id == cat_id,
                )
            )
            if existing:
                return rel
            self._merge_and_commit(session, record)
        return rel

    def vector_search_items(self, query_vec: list[float], top_k: int) -> list[tuple[str, float]]:
        if not self._use_vector_type:
            return super().vector_search_items(query_vec, top_k)
        with self._session() as session:
            distance = self._models.MemoryItem.embedding.cosine_distance(query_vec)
            stmt = (
                select(self._models.MemoryItem.id, (1 - distance).label("score"))
                .where(
                    self._models.MemoryItem.scope_key == self.scope_key,
                    self._models.MemoryItem.embedding.isnot(None),
                )
                .order_by(distance)
                .limit(top_k)
            )
            rows = session.execute(stmt).all()
        return [(rid, float(score)) for rid, score in rows]
