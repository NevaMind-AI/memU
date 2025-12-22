from __future__ import annotations

from typing import Any

from memu.database.models import MemoryItem, MemoryType
from memu.database.postgres.repositories.base import PostgresRepoBase
from memu.database.postgres.session import SessionManager
from memu.database.repositories.memory_item import MemoryItemRepo
from memu.database.state import DatabaseState


class PostgresMemoryItemRepo(PostgresRepoBase, MemoryItemRepo):
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

    def create_item(
        self, *, resource_id: str, memory_type: MemoryType, summary: str, embedding: list[float]
    ) -> MemoryItem:
        item = self._memory_item_model(
            resource_id=resource_id,
            memory_type=memory_type,
            summary=summary,
            embedding=self._prepare_embedding(embedding),
            created_at=self._now(),
            updated_at=self._now(),
        )

        with self._sessions.session() as session:
            session.add(item)
            session.commit()
            session.refresh(item)

        self.items[item.id] = item
        return item

    def vector_search_items(self, query_vec: list[float], top_k: int) -> list[tuple[str, float]]:
        if not self._use_vector:
            return self._vector_search_local(query_vec, top_k)
        from sqlmodel import select

        with self._sessions.session() as session:
            distance = self._sqla_models.MemoryItem.embedding.cosine_distance(query_vec)
            stmt = (
                select(self._sqla_models.MemoryItem.id, (1 - distance).label("score"))
                .where(self._sqla_models.MemoryItem.embedding.isnot(None))
                .order_by(distance)
                .limit(top_k)
            )
            rows = session.execute(stmt).all()
        return [(rid, float(score)) for rid, score in rows]

    def load_existing(self) -> None:
        from sqlmodel import select

        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.MemoryItem)).all()
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                self.items[row.id] = row

    def _vector_search_local(self, query_vec: list[float], top_k: int) -> list[tuple[str, float]]:
        scored: list[tuple[str, float]] = []
        for item in self.items.values():
            if item.embedding is None:
                continue
            score = self._cosine(query_vec, item.embedding)
            scored.append((item.id, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        denom = (sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5) + 1e-9
        return float(sum(x * y for x, y in zip(a, b, strict=True)) / denom)


__all__ = ["PostgresMemoryItemRepo"]
