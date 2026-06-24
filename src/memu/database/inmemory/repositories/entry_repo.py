from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any, override

import pendulum

from memu.database.inmemory.repositories.filter import matches_where
from memu.database.inmemory.state import InMemoryState
from memu.database.models import Entry, compute_content_hash
from memu.database.repositories.entry import EntryRepo
from memu.vector import cosine_topk, cosine_topk_salience


class InMemoryEntryRepository(EntryRepo):
    def __init__(self, *, state: InMemoryState, entry_model: type[Entry]) -> None:
        self._state = state
        self.entry_model = entry_model
        self.entries: dict[str, Entry] = self._state.entries

    def list_entries(
        self, where: Mapping[str, Any] | None = None, *, lane: str | None = None
    ) -> dict[str, Entry]:
        result = self.entries if not where else {
            eid: entry for eid, entry in self.entries.items() if matches_where(entry, where)
        }
        if lane is not None:
            result = {eid: entry for eid, entry in result.items() if getattr(entry, "lane", None) == lane}
        return dict(result)

    def list_entries_by_ref_ids(
        self, ref_ids: list[str], where: Mapping[str, Any] | None = None
    ) -> dict[str, Entry]:
        if not ref_ids:
            return {}
        ref_id_set = set(ref_ids)
        result: dict[str, Entry] = {}
        for eid, entry in self.entries.items():
            if where and not matches_where(entry, where):
                continue
            entry_ref_id = (entry.extra or {}).get("ref_id")
            if entry_ref_id and entry_ref_id in ref_id_set:
                result[eid] = entry
        return result

    def clear_entries(
        self, where: Mapping[str, Any] | None = None, *, lane: str | None = None
    ) -> dict[str, Entry]:
        if not where and lane is None:
            matches = self.entries.copy()
            self.entries.clear()
            return matches
        matches = self.list_entries(where, lane=lane)
        for eid in matches:
            self.entries.pop(eid, None)
        return matches

    def _find_by_hash(self, content_hash: str, user_data: dict[str, Any]) -> Entry | None:
        for entry in self.entries.values():
            entry_hash = (entry.extra or {}).get("content_hash")
            if entry_hash != content_hash:
                continue
            if matches_where(entry, user_data):
                return entry
        return None

    def create_entry(
        self,
        *,
        lane: str,
        source_id: str | None,
        entry_kind: str,
        text: str,
        embedding: list[float],
        user_data: dict[str, Any],
        source_path: str | None = None,
        reinforce: bool = False,
        tool_record: dict[str, Any] | None = None,
    ) -> Entry:
        if reinforce and entry_kind != "tool":
            return self.create_entry_reinforce(
                lane=lane,
                source_id=source_id,
                entry_kind=entry_kind,
                text=text,
                embedding=embedding,
                user_data=user_data,
                source_path=source_path,
            )

        extra: dict[str, Any] = {}
        if tool_record:
            for key in ("when_to_use", "metadata", "tool_calls"):
                if tool_record.get(key) is not None:
                    extra[key] = tool_record[key]

        eid = str(uuid.uuid4())
        entry = self.entry_model(
            id=eid,
            lane=lane,
            source_id=source_id,
            source_path=source_path,
            entry_kind=entry_kind,
            text=text,
            embedding=embedding,
            extra=extra if extra else {},
            **user_data,
        )
        self.entries[eid] = entry
        return entry

    def create_entry_reinforce(
        self,
        *,
        lane: str,
        source_id: str | None,
        entry_kind: str,
        text: str,
        embedding: list[float],
        user_data: dict[str, Any],
        source_path: str | None = None,
    ) -> Entry:
        content_hash = compute_content_hash(text, entry_kind)
        existing = self._find_by_hash(content_hash, user_data)
        if existing:
            current_extra = existing.extra or {}
            current_count = current_extra.get("reinforcement_count", 1)
            existing.extra = {
                **current_extra,
                "reinforcement_count": current_count + 1,
                "last_reinforced_at": pendulum.now("UTC").isoformat(),
            }
            existing.updated_at = pendulum.now("UTC")
            return existing

        eid = str(uuid.uuid4())
        now = pendulum.now("UTC")
        entry_extra = user_data.pop("extra", {}) if "extra" in user_data else {}
        entry_extra.update({
            "content_hash": content_hash,
            "reinforcement_count": 1,
            "last_reinforced_at": now.isoformat(),
        })
        entry = self.entry_model(
            id=eid,
            lane=lane,
            source_id=source_id,
            source_path=source_path,
            entry_kind=entry_kind,
            text=text,
            embedding=embedding,
            extra=entry_extra,
            **user_data,
        )
        self.entries[eid] = entry
        return entry

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

    def load_existing(self) -> None:
        return None

    def get_entry(self, entry_id: str) -> Entry | None:
        return self.entries.get(entry_id)

    @staticmethod
    def _parse_datetime(dt_str: str | None) -> pendulum.DateTime | None:
        if dt_str is None:
            return None
        try:
            parsed = pendulum.parse(dt_str)
        except (ValueError, TypeError):
            return None
        else:
            if isinstance(parsed, pendulum.DateTime):
                return parsed
            return None

    @override
    def delete_entry(self, entry_id: str) -> None:
        self.entries.pop(entry_id, None)

    @override
    def update_entry(
        self,
        *,
        entry_id: str,
        entry_kind: str | None = None,
        text: str | None = None,
        embedding: list[float] | None = None,
        extra: dict[str, Any] | None = None,
        tool_record: dict[str, Any] | None = None,
    ) -> Entry:
        entry = self.entries.get(entry_id)
        if entry is None:
            msg = f"Entry with id {entry_id} not found"
            raise KeyError(msg)

        if entry_kind is not None:
            entry.entry_kind = entry_kind
        if text is not None:
            entry.text = text
        if embedding is not None:
            entry.embedding = embedding

        current_extra = entry.extra or {}
        if extra is not None:
            current_extra = {**current_extra, **extra}
        if tool_record is not None:
            for key in ("when_to_use", "metadata", "tool_calls"):
                if tool_record.get(key) is not None:
                    current_extra[key] = tool_record[key]
        if extra is not None or tool_record is not None:
            entry.extra = current_extra

        self.entries[entry_id] = entry
        return entry


__all__ = ["InMemoryEntryRepository"]
