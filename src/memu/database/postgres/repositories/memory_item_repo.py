from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from memu.database.models import MemoryItem, MemoryType
from memu.database.postgres.repositories.base import PostgresRepoBase
from memu.database.postgres.session import SessionManager
from memu.database.state import DatabaseState


class PostgresMemoryItemRepo(PostgresRepoBase):
    def __init__(
        self,
        *,
        state: DatabaseState,
        memory_item_model: type[MemoryItem],
        sqla_models: Any,
        sessions: SessionManager,
        scope_fields: list[str],
        use_vector: bool,
    ) -> None:
        super().__init__(
            state=state, sqla_models=sqla_models, sessions=sessions, scope_fields=scope_fields, use_vector=use_vector
        )
        self._memory_item_model = memory_item_model
        self.items: dict[str, MemoryItem] = self._state.items

    def get_item(self, memory_id: str) -> MemoryItem | None:
        from sqlmodel import select

        with self._sessions.session() as session:
            row = session.scalar(
                select(self._sqla_models.MemoryItem).where(self._sqla_models.MemoryItem.id == memory_id)
            )
            if row:
                row.embedding = self._normalize_embedding(row.embedding)
                return self._cache_item(row)
        return None

    def list_items(self, where: Mapping[str, Any] | None = None) -> dict[str, MemoryItem]:
        from sqlmodel import select

        filters = self._build_filters(self._sqla_models.MemoryItem, where)
        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.MemoryItem).where(*filters)).all()
            result: dict[str, MemoryItem] = {}
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                item = self._cache_item(row)
                result[item.id] = item
        return result

    def create_item(
        self,
        *,
        resource_id: str | None = None,
        memory_type: MemoryType,
        summary: str,
        embedding: list[float],
        user_data: dict[str, Any],
    ) -> MemoryItem:
        item = self._memory_item_model(
            resource_id=resource_id,
            memory_type=memory_type,
            summary=summary,
            embedding=self._prepare_embedding(embedding),
            **user_data,
            created_at=self._now(),
            updated_at=self._now(),
        )

        with self._sessions.session() as session:
            session.add(item)
            session.commit()
            session.refresh(item)

        self.items[item.id] = item
        return item

    def update_item(
        self,
        *,
        item_id: str,
        memory_type: MemoryType | None = None,
        summary: str | None = None,
        embedding: list[float] | None = None,
    ) -> MemoryItem:
        from sqlmodel import select

        now = self._now()
        with self._sessions.session() as session:
            item = session.scalar(
                select(self._sqla_models.MemoryItem).where(self._sqla_models.MemoryItem.id == item_id)
            )
            if item is None:
                msg = f"Item with id {item_id} not found"
                raise KeyError(msg)

            if memory_type is not None:
                item.memory_type = memory_type
            if summary is not None:
                item.summary = summary
            if embedding is not None:
                item.embedding = self._prepare_embedding(embedding)

            item.updated_at = now
            session.add(item)
            session.commit()
            session.refresh(item)
            item.embedding = self._normalize_embedding(item.embedding)

        return self._cache_item(item)

    def delete_item(self, item_id: str) -> None:
        from sqlmodel import delete

        with self._sessions.session() as session:
            session.exec(delete(self._sqla_models.MemoryItem).where(self._sqla_models.MemoryItem.id == item_id))
            session.commit()

    def vector_search_items(
        self, query_vec: list[float], top_k: int, where: Mapping[str, Any] | None = None
    ) -> list[tuple[str, float]]:
        if not self._use_vector:
            return self._vector_search_local(query_vec, top_k, where=where)
        from sqlmodel import select

        distance = self._sqla_models.MemoryItem.embedding.cosine_distance(query_vec)
        filters = [self._sqla_models.MemoryItem.embedding.isnot(None)]
        filters.extend(self._build_filters(self._sqla_models.MemoryItem, where))
        stmt = (
            select(self._sqla_models.MemoryItem.id, (1 - distance).label("score"))
            .where(*filters)
            .order_by(distance)
            .limit(top_k)
        )
        with self._sessions.session() as session:
            rows = session.execute(stmt).all()
        return [(rid, float(score)) for rid, score in rows]

    def load_existing(self) -> None:
        from sqlmodel import select

        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.MemoryItem)).all()
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                self._cache_item(row)

    def _vector_search_local(
        self, query_vec: list[float], top_k: int, where: Mapping[str, Any] | None = None
    ) -> list[tuple[str, float]]:
        scored: list[tuple[str, float]] = []
        for item in self.items.values():
            if item.embedding is None:
                continue
            if not self._matches_where(item, where):
                continue
            score = self._cosine(query_vec, item.embedding)
            scored.append((item.id, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _cache_item(self, item: MemoryItem) -> MemoryItem:
        self.items[item.id] = item
        return item

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        denom = (sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5) + 1e-9
        return float(sum(x * y for x, y in zip(a, b, strict=True)) / denom)


__all__ = ["PostgresMemoryItemRepo"]
