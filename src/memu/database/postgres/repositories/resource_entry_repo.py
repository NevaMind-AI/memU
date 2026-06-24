from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from memu.database.models import ResourceEntry
from memu.database.postgres.repositories.base import PostgresRepoBase
from memu.database.postgres.session import SessionManager
from memu.database.repositories.resource_entry import ResourceEntryRepo
from memu.database.state import DatabaseState


class PostgresResourceEntryRepo(PostgresRepoBase, ResourceEntryRepo):
    def __init__(
        self,
        *,
        state: DatabaseState,
        resource_entry_model: type[ResourceEntry],
        sqla_models: Any,
        sessions: SessionManager,
        scope_fields: list[str],
    ) -> None:
        super().__init__(state=state, sqla_models=sqla_models, sessions=sessions, scope_fields=scope_fields)
        self._resource_entry_model = resource_entry_model
        self.relations: list[ResourceEntry] = self._state.relations

    def list_relations(self, where: Mapping[str, Any] | None = None) -> list[ResourceEntry]:
        from sqlmodel import select

        filters = self._build_filters(self._sqla_models.ResourceEntry, where)
        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.ResourceEntry).where(*filters)).all()
        return [self._row_to_record(row) for row in rows]

    def link_entry_resource(self, entry_id: str, resource_id: str, user_data: dict[str, Any]) -> ResourceEntry:
        from sqlmodel import select

        for rel in self.relations:
            if rel.entry_id == entry_id and rel.resource_id == resource_id:
                return rel

        now = self._now()
        new_rel = self._resource_entry_model(
            entry_id=entry_id,
            resource_id=resource_id,
            **user_data,
            created_at=now,
            updated_at=now,
        )

        with self._sessions.session() as session:
            existing = session.scalar(
                select(self._sqla_models.ResourceEntry).where(
                    self._sqla_models.ResourceEntry.entry_id == entry_id,
                    self._sqla_models.ResourceEntry.resource_id == resource_id,
                )
            )
            if existing:
                return self._cache_relation(self._row_to_record(existing))

            session.add(new_rel)
            session.commit()
            session.refresh(new_rel)
            record = self._row_to_record(new_rel)

        return self._cache_relation(record)

    def unlink_entry_resource(self, entry_id: str, resource_id: str) -> None:
        from sqlmodel import delete

        with self._sessions.session() as session:
            session.exec(
                delete(self._sqla_models.ResourceEntry).where(
                    self._sqla_models.ResourceEntry.entry_id == entry_id,
                    self._sqla_models.ResourceEntry.resource_id == resource_id,
                )
            )
            session.commit()
        self.relations[:] = [
            r for r in self.relations if not (r.entry_id == entry_id and r.resource_id == resource_id)
        ]

    def unlink_entry(self, entry_id: str) -> list[ResourceEntry]:
        from sqlmodel import delete, select

        with self._sessions.session() as session:
            rows = session.scalars(
                select(self._sqla_models.ResourceEntry).where(self._sqla_models.ResourceEntry.entry_id == entry_id)
            ).all()
            removed = [self._row_to_record(row) for row in rows]
            if removed:
                session.exec(
                    delete(self._sqla_models.ResourceEntry).where(
                        self._sqla_models.ResourceEntry.entry_id == entry_id
                    )
                )
                session.commit()
        self.relations[:] = [r for r in self.relations if r.entry_id != entry_id]
        return removed

    def clear_relations(self, where: Mapping[str, Any] | None = None) -> list[ResourceEntry]:
        from sqlmodel import delete, select

        filters = self._build_filters(self._sqla_models.ResourceEntry, where)
        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.ResourceEntry).where(*filters)).all()
            removed = [self._row_to_record(row) for row in rows]
            if removed:
                session.exec(delete(self._sqla_models.ResourceEntry).where(*filters))
                session.commit()
        removed_ids = {rel.id for rel in removed}
        self.relations[:] = [r for r in self.relations if r.id not in removed_ids]
        return removed

    def get_entry_resources(self, entry_id: str) -> list[ResourceEntry]:
        from sqlmodel import select

        with self._sessions.session() as session:
            rows = session.scalars(
                select(self._sqla_models.ResourceEntry).where(self._sqla_models.ResourceEntry.entry_id == entry_id)
            ).all()
        return [self._row_to_record(row) for row in rows]

    def load_existing(self) -> None:
        from sqlmodel import select

        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.ResourceEntry)).all()
            self.relations.clear()
            for row in rows:
                self._cache_relation(self._row_to_record(row))

    def _row_to_record(self, row: Any) -> ResourceEntry:
        return ResourceEntry(
            id=row.id,
            entry_id=row.entry_id,
            resource_id=row.resource_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            **self._scope_kwargs_from(row),
        )

    def _cache_relation(self, rel: ResourceEntry) -> ResourceEntry:
        self.relations.append(rel)
        return rel


__all__ = ["PostgresResourceEntryRepo"]
