from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

import pendulum

from memu.database.models import Entry, compute_content_hash
from memu.database.postgres.repositories.base import PostgresRepoBase
from memu.database.postgres.session import SessionManager
from memu.database.repositories.entry import EntryRepo
from memu.database.state import DatabaseState
from memu.vector import cosine_topk, cosine_topk_salience


class PostgresEntryRepo(PostgresRepoBase, EntryRepo):
    def __init__(
        self,
        *,
        state: DatabaseState,
        entry_model: type[Entry],
        sqla_models: Any,
        sessions: SessionManager,
        scope_fields: list[str],
        use_vector: bool,
    ) -> None:
        super().__init__(
            state=state, sqla_models=sqla_models, sessions=sessions, scope_fields=scope_fields, use_vector=use_vector
        )
        self._entry_model = entry_model
        self.entries: dict[str, Entry] = self._state.entries

    def get_entry(self, entry_id: str) -> Entry | None:
        from sqlmodel import select

        with self._sessions.session() as session:
            row = session.scalar(select(self._sqla_models.Entry).where(self._sqla_models.Entry.id == entry_id))
            if row:
                row.embedding = self._normalize_embedding(row.embedding)
                return self._cache_entry(row)
        return None

    def list_entries(self, where: Mapping[str, Any] | None = None, *, lane: str | None = None) -> dict[str, Entry]:
        from sqlmodel import select

        model = self._sqla_models.Entry
        filters = self._build_filters(model, where)
        if lane is not None:
            filters.append(model.lane == lane)
        with self._sessions.session() as session:
            rows = session.scalars(select(model).where(*filters)).all()
            result: dict[str, Entry] = {}
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                entry = self._cache_entry(row)
                result[entry.id] = entry
        return result

    def list_entries_by_ref_ids(self, ref_ids: list[str], where: Mapping[str, Any] | None = None) -> dict[str, Entry]:
        if not ref_ids:
            return {}

        from sqlmodel import select

        model = self._sqla_models.Entry
        filters = self._build_filters(model, where)
        ref_id_col = model.extra["ref_id"].astext
        filters.append(ref_id_col.isnot(None))
        filters.append(ref_id_col.in_(ref_ids))

        with self._sessions.session() as session:
            rows = session.scalars(select(model).where(*filters)).all()
            result: dict[str, Entry] = {}
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                entry = self._cache_entry(row)
                result[entry.id] = entry
        return result

    def clear_entries(self, where: Mapping[str, Any] | None = None, *, lane: str | None = None) -> dict[str, Entry]:
        from sqlmodel import delete, select

        model = self._sqla_models.Entry
        filters = self._build_filters(model, where)
        if lane is not None:
            filters.append(model.lane == lane)
        with self._sessions.session() as session:
            rows = session.scalars(select(model).where(*filters)).all()
            deleted: dict[str, Entry] = {}
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                deleted[row.id] = row

            if not deleted:
                return {}

            session.exec(delete(model).where(*filters))
            session.commit()

            for entry_id in deleted:
                self.entries.pop(entry_id, None)

        return deleted

    def create_entry(
        self,
        *,
        lane: str,
        source_id: str | None,
        entry_type: str,
        text: str,
        embedding: list[float],
        user_data: dict[str, Any],
        source_path: str | None = None,
        reinforce: bool = False,
    ) -> Entry:
        if reinforce:
            return self.create_entry_reinforce(
                lane=lane,
                source_id=source_id,
                entry_type=entry_type,
                text=text,
                embedding=embedding,
                user_data=user_data,
                source_path=source_path,
            )

        entry = self._entry_model(
            lane=lane,
            source_id=source_id,
            source_path=source_path,
            entry_type=entry_type,
            text=text,
            embedding=self._prepare_embedding(embedding),
            extra={},
            **user_data,
            created_at=self._now(),
            updated_at=self._now(),
        )

        with self._sessions.session() as session:
            session.add(entry)
            session.commit()
            session.refresh(entry)

        entry.embedding = self._normalize_embedding(entry.embedding)
        return self._cache_entry(entry)

    def create_entry_reinforce(
        self,
        *,
        lane: str,
        source_id: str | None,
        entry_type: str,
        text: str,
        embedding: list[float],
        user_data: dict[str, Any],
        source_path: str | None = None,
    ) -> Entry:
        from sqlmodel import select

        model = self._sqla_models.Entry
        content_hash = compute_content_hash(text, entry_type)
        entry_extra = user_data.pop("extra", {}) if "extra" in user_data else {}

        with self._sessions.session() as session:
            content_hash_col = model.extra["content_hash"].astext
            filters = [content_hash_col == content_hash]
            filters.extend(self._build_filters(model, user_data))

            existing = session.scalar(select(model).where(*filters))

            if existing:
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
                return self._cache_entry(existing)

            now = self._now()
            entry_extra.update({
                "content_hash": content_hash,
                "reinforcement_count": 1,
                "last_reinforced_at": now.isoformat(),
            })
            entry = self._entry_model(
                lane=lane,
                source_id=source_id,
                source_path=source_path,
                entry_type=entry_type,
                text=text,
                embedding=self._prepare_embedding(embedding),
                **user_data,
                created_at=now,
                updated_at=now,
                extra=entry_extra,
            )

            session.add(entry)
            session.commit()
            session.refresh(entry)

        entry.embedding = self._normalize_embedding(entry.embedding)
        return self._cache_entry(entry)

    def update_entry(
        self,
        *,
        entry_id: str,
        entry_type: str | None = None,
        text: str | None = None,
        embedding: list[float] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> Entry:
        from sqlmodel import select

        model = self._sqla_models.Entry
        now = self._now()
        with self._sessions.session() as session:
            entry = session.scalar(select(model).where(model.id == entry_id))
            if entry is None:
                msg = f"Entry with id {entry_id} not found"
                raise KeyError(msg)

            if entry_type is not None:
                entry.entry_type = entry_type
            if text is not None:
                entry.text = text
            if embedding is not None:
                entry.embedding = self._prepare_embedding(embedding)

            if extra is not None:
                entry.extra = {**(entry.extra or {}), **extra}

            entry.updated_at = now
            session.add(entry)
            session.commit()
            session.refresh(entry)
            entry.embedding = self._normalize_embedding(entry.embedding)

        return self._cache_entry(entry)

    def delete_entry(self, entry_id: str) -> None:
        from sqlmodel import delete

        with self._sessions.session() as session:
            session.exec(delete(self._sqla_models.Entry).where(self._sqla_models.Entry.id == entry_id))
            session.commit()
        self.entries.pop(entry_id, None)

    def vector_search_entries(
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
        *,
        lane: str | None = None,
        ranking: str = "similarity",
        recency_decay_days: float = 30.0,
    ) -> list[tuple[str, float]]:
        if not self._use_vector or ranking == "salience":
            return self._vector_search_local(
                query_vec, top_k, where=where, lane=lane, ranking=ranking, recency_decay_days=recency_decay_days
            )

        from sqlmodel import select

        model = self._sqla_models.Entry
        distance = model.embedding.cosine_distance(query_vec)
        filters = [model.embedding.isnot(None)]
        filters.extend(self._build_filters(model, where))
        if lane is not None:
            filters.append(model.lane == lane)
        stmt = select(model.id, (1 - distance).label("score")).where(*filters).order_by(distance).limit(top_k)
        with self._sessions.session() as session:
            rows = session.execute(stmt).all()
        return [(rid, float(score)) for rid, score in rows]

    def load_existing(self) -> None:
        from sqlmodel import select

        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.Entry)).all()
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                self._cache_entry(row)

    def _vector_search_local(
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
        *,
        lane: str | None = None,
        ranking: str = "similarity",
        recency_decay_days: float = 30.0,
    ) -> list[tuple[str, float]]:
        pool = self.list_entries(where, lane=lane)

        if ranking == "salience":
            corpus = [
                (
                    e.id,
                    e.embedding,
                    (e.extra or {}).get("reinforcement_count", 1),
                    self._parse_datetime((e.extra or {}).get("last_reinforced_at")),
                )
                for e in pool.values()
            ]
            return cosine_topk_salience(query_vec, corpus, k=top_k, recency_decay_days=recency_decay_days)

        return cosine_topk(query_vec, [(e.id, e.embedding) for e in pool.values()], k=top_k)

    def _cache_entry(self, entry: Entry) -> Entry:
        self.entries[entry.id] = entry
        return entry

    @staticmethod
    def _parse_datetime(dt_str: str | None) -> datetime | None:
        if dt_str is None:
            return None
        try:
            parsed = pendulum.parse(dt_str)
        except (ValueError, TypeError):
            return None
        else:
            if isinstance(parsed, datetime):
                return parsed
            return None


__all__ = ["PostgresEntryRepo"]
