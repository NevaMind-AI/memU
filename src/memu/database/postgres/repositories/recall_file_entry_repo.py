from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from memu.database.models import RecallFileEntry
from memu.database.postgres.repositories.base import PostgresRepoBase
from memu.database.postgres.session import SessionManager
from memu.database.repositories.recall_file_entry import RecallFileEntryRepo
from memu.database.state import DatabaseState


class PostgresRecallFileEntryRepo(PostgresRepoBase, RecallFileEntryRepo):
    def __init__(
        self,
        *,
        state: DatabaseState,
        recall_file_entry_model: type[RecallFileEntry],
        sqla_models: Any,
        sessions: SessionManager,
        scope_fields: list[str],
    ) -> None:
        super().__init__(state=state, sqla_models=sqla_models, sessions=sessions, scope_fields=scope_fields)
        self._recall_file_entry_model = recall_file_entry_model
        self.relations: list[RecallFileEntry] = self._state.relations

    def list_relations(self, where: Mapping[str, Any] | None = None) -> list[RecallFileEntry]:
        from sqlmodel import select

        filters = self._build_filters(self._sqla_models.RecallFileEntry, where)
        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.RecallFileEntry).where(*filters)).all()
        return [self._cache_relation(row) for row in rows]

    def link_item_category(self, item_id: str, cat_id: str, user_data: dict[str, Any]) -> RecallFileEntry:
        from sqlmodel import select

        # Avoid duplicate inserts using local cache
        for rel in self.relations:
            if rel.item_id == item_id and rel.category_id == cat_id:
                return rel

        now = self._now()
        new_rel = self._recall_file_entry_model(
            item_id=item_id,
            category_id=cat_id,
            **user_data,
            created_at=now,
            updated_at=now,
        )

        with self._sessions.session() as session:
            existing = session.scalar(
                select(self._sqla_models.RecallFileEntry).where(
                    self._sqla_models.RecallFileEntry.item_id == item_id,
                    self._sqla_models.RecallFileEntry.category_id == cat_id,
                )
            )
            if existing:
                return self._cache_relation(existing)

            session.add(new_rel)
            session.commit()
            session.refresh(new_rel)

        return self._cache_relation(new_rel)

    def unlink_item_category(self, item_id: str, cat_id: str) -> None:
        from sqlmodel import delete

        with self._sessions.session() as session:
            session.exec(
                delete(self._sqla_models.RecallFileEntry).where(
                    self._sqla_models.RecallFileEntry.item_id == item_id,
                    self._sqla_models.RecallFileEntry.category_id == cat_id,
                )
            )
            session.commit()
        self.relations[:] = [r for r in self.relations if not (r.item_id == item_id and r.category_id == cat_id)]

    def _row_to_record(self, row: Any) -> RecallFileEntry:
        return RecallFileEntry(
            id=row.id,
            item_id=row.item_id,
            category_id=row.category_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            **self._scope_kwargs_from(row),
        )

    def unlink_item(self, item_id: str) -> list[RecallFileEntry]:
        from sqlmodel import delete, select

        with self._sessions.session() as session:
            rows = session.scalars(
                select(self._sqla_models.RecallFileEntry).where(self._sqla_models.RecallFileEntry.item_id == item_id)
            ).all()
            removed = [self._row_to_record(row) for row in rows]
            if removed:
                session.exec(
                    delete(self._sqla_models.RecallFileEntry).where(
                        self._sqla_models.RecallFileEntry.item_id == item_id
                    )
                )
                session.commit()
        self.relations[:] = [r for r in self.relations if r.item_id != item_id]
        return removed

    def clear_relations(self, where: Mapping[str, Any] | None = None) -> list[RecallFileEntry]:
        from sqlmodel import delete, select

        filters = self._build_filters(self._sqla_models.RecallFileEntry, where)
        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.RecallFileEntry).where(*filters)).all()
            removed = [self._row_to_record(row) for row in rows]
            if removed:
                session.exec(delete(self._sqla_models.RecallFileEntry).where(*filters))
                session.commit()
        removed_ids = {rel.id for rel in removed}
        self.relations[:] = [r for r in self.relations if r.id not in removed_ids]
        return removed

    def get_item_categories(self, item_id: str) -> list[RecallFileEntry]:
        from sqlmodel import select

        with self._sessions.session() as session:
            rows = session.scalars(
                select(self._sqla_models.RecallFileEntry).where(self._sqla_models.RecallFileEntry.item_id == item_id)
            ).all()
        return [self._cache_relation(row) for row in rows]

    def load_existing(self) -> None:
        from sqlmodel import select

        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.RecallFileEntry)).all()
            for row in rows:
                self._cache_relation(row)

    def _cache_relation(self, rel: RecallFileEntry) -> RecallFileEntry:
        self.relations.append(rel)
        return rel


__all__ = ["PostgresRecallFileEntryRepo"]
