from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from memu.database.models import MemoryItem, MemoryType, compute_content_hash
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

    def list_items_by_ref_ids(
        self, ref_ids: list[str], where: Mapping[str, Any] | None = None
    ) -> dict[str, MemoryItem]:
        """List items by their ref_id in the extra column.

        Args:
            ref_ids: List of ref_ids to query.
            where: Additional filter conditions.

        Returns:
            Dict mapping item_id -> MemoryItem for items whose extra->>'ref_id' is in ref_ids.
        """
        if not ref_ids:
            return {}

        from sqlmodel import select

        filters = self._build_filters(self._sqla_models.MemoryItem, where)
        # Add filter for extra->>'ref_id' IN ref_ids (only rows with ref_id key)
        ref_id_col = self._sqla_models.MemoryItem.extra["ref_id"].astext
        filters.append(ref_id_col.isnot(None))
        filters.append(ref_id_col.in_(ref_ids))

        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.MemoryItem).where(*filters)).all()
            result: dict[str, MemoryItem] = {}
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                item = self._cache_item(row)
                result[item.id] = item
        return result

    def clear_items(self, where: Mapping[str, Any] | None = None) -> dict[str, MemoryItem]:
        from sqlmodel import delete, select

        filters = self._build_filters(self._sqla_models.MemoryItem, where)
        with self._sessions.session() as session:
            # First get the objects to delete
            rows = session.scalars(select(self._sqla_models.MemoryItem).where(*filters)).all()
            deleted: dict[str, MemoryItem] = {}
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                deleted[row.id] = row

            if not deleted:
                return {}

            # Delete from database
            session.exec(delete(self._sqla_models.MemoryItem).where(*filters))
            session.commit()

            # Clean up cache
            for item_id in deleted:
                self.items.pop(item_id, None)

        return deleted

    def create_item(
        self,
        *,
        resource_id: str | None = None,
        memory_type: MemoryType,
        summary: str,
        embedding: list[float],
        user_data: dict[str, Any],
        reinforce: bool = False,
        tool_record: dict[str, Any] | None = None,
    ) -> MemoryItem:
        if reinforce and memory_type != "tool":
            return self.create_item_reinforce(
                resource_id=resource_id,
                memory_type=memory_type,
                summary=summary,
                embedding=embedding,
                user_data=user_data,
            )

        # Build extra dict with tool_record fields at top level
        extra: dict[str, Any] = {}
        if tool_record:
            if tool_record.get("when_to_use") is not None:
                extra["when_to_use"] = tool_record["when_to_use"]
            if tool_record.get("metadata") is not None:
                extra["metadata"] = tool_record["metadata"]
            if tool_record.get("tool_calls") is not None:
                extra["tool_calls"] = tool_record["tool_calls"]

        item = self._memory_item_model(
            resource_id=resource_id,
            memory_type=memory_type,
            summary=summary,
            embedding=self._prepare_embedding(embedding),
            extra=extra if extra else {},
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

    def create_item_reinforce(
        self,
        *,
        resource_id: str | None = None,
        memory_type: MemoryType,
        summary: str,
        embedding: list[float],
        user_data: dict[str, Any],
    ) -> MemoryItem:
        from sqlmodel import select

        content_hash = compute_content_hash(summary, memory_type)

        with self._sessions.session() as session:
            # Check for existing item with same hash in same scope (deduplication)
            # Use extra->>'content_hash' for query performance
            content_hash_col = self._sqla_models.MemoryItem.extra["content_hash"].astext
            filters = [content_hash_col == content_hash]
            filters.extend(self._build_filters(self._sqla_models.MemoryItem, user_data))

            existing = session.scalar(select(self._sqla_models.MemoryItem).where(*filters))

            if existing:
                # Reinforce existing memory instead of creating duplicate
                current_extra = existing.extra or {}
                current_count = current_extra.get("reinforcement_count", 1)
                existing.extra = {
                    **current_extra,
                    "reinforcement_count": current_count + 1,
                    "last_reinforced_at": self._now().isoformat(),
                }
                existing.updated_at = self._now()
                session.add(existing)
                session.commit()
                session.refresh(existing)
                existing.embedding = self._normalize_embedding(existing.embedding)
                return self._cache_item(existing)

            # Create new item with salience tracking in extra
            now = self._now()

            item = self._memory_item_model(
                resource_id=resource_id,
                memory_type=memory_type,
                summary=summary,
                embedding=self._prepare_embedding(embedding),
                **user_data,
                created_at=now,
                updated_at=now,
                extra={
                    "content_hash": content_hash,
                    "reinforcement_count": 1,
                    "last_reinforced_at": now.isoformat(),
                },
            )

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
        extra: dict[str, Any] | None = None,
        tool_record: dict[str, Any] | None = None,
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

            # Merge extra and tool_record into existing extra dict
            current_extra = item.extra or {}
            if extra is not None:
                current_extra = {**current_extra, **extra}
            if tool_record is not None:
                # Merge tool_record fields at top level
                for key in ("when_to_use", "metadata", "tool_calls"):
                    if tool_record.get(key) is not None:
                        current_extra[key] = tool_record[key]
            if extra is not None or tool_record is not None:
                item.extra = current_extra

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
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
        *,
        ranking: str = "similarity",
        recency_decay_days: float = 30.0,
    ) -> list[tuple[str, float]]:
        if not self._use_vector or ranking == "salience":
            # For salience ranking or when pgvector is not available, use local search
            return self._vector_search_local(
                query_vec, top_k, where=where, ranking=ranking, recency_decay_days=recency_decay_days
            )

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
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
        *,
        ranking: str = "similarity",
        recency_decay_days: float = 30.0,
    ) -> list[tuple[str, float]]:
        scored: list[tuple[str, float]] = []
        for item in self.items.values():
            if item.embedding is None:
                continue
            if not self._matches_where(item, where):
                continue

            similarity = self._cosine(query_vec, item.embedding)

            if ranking == "salience":
                # Salience-aware scoring - read from extra dict
                extra = item.extra or {}
                reinforcement_count = extra.get("reinforcement_count", 1)
                last_reinforced_at = self._parse_datetime(extra.get("last_reinforced_at"))
                score = self._salience_score(
                    similarity,
                    reinforcement_count,
                    last_reinforced_at,
                    recency_decay_days,
                )
            else:
                score = similarity

            scored.append((item.id, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    @staticmethod
    def _salience_score(
        similarity: float,
        reinforcement_count: int,
        last_reinforced_at: datetime | None,
        recency_decay_days: float,
    ) -> float:
        """Compute salience score: similarity * reinforcement * recency."""
        reinforcement_factor = math.log(reinforcement_count + 1)

        if last_reinforced_at is None:
            recency_factor = 0.5
        else:
            now = datetime.now(last_reinforced_at.tzinfo) if last_reinforced_at.tzinfo else datetime.utcnow()
            days_ago = (now - last_reinforced_at).total_seconds() / 86400
            recency_factor = math.exp(-0.693 * days_ago / recency_decay_days)

        return similarity * reinforcement_factor * recency_factor

    def _cache_item(self, item: MemoryItem) -> MemoryItem:
        self.items[item.id] = item
        return item

    @staticmethod
    def _parse_datetime(dt_str: str | None) -> datetime | None:
        """Parse ISO datetime string from extra dict."""
        if dt_str is None:
            return None
        try:
            import pendulum

            parsed = pendulum.parse(dt_str)
        except (ValueError, TypeError):
            return None
        else:
            if isinstance(parsed, datetime):
                return parsed
            return None

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        denom = (sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5) + 1e-9
        return float(sum(x * y for x, y in zip(a, b, strict=True)) / denom)


__all__ = ["PostgresMemoryItemRepo"]
