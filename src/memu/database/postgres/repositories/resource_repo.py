from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from memu.database.models import Resource
from memu.database.postgres.repositories.base import PostgresRepoBase
from memu.database.postgres.session import SessionManager
from memu.database.repositories.resource import ResourceRepo
from memu.database.state import DatabaseState


class PostgresResourceRepo(PostgresRepoBase, ResourceRepo):
    def __init__(
        self,
        *,
        state: DatabaseState,
        resource_model: type[Resource],
        sqla_models: Any,
        sessions: SessionManager,
        scope_fields: list[str],
    ) -> None:
        super().__init__(state=state, sqla_models=sqla_models, sessions=sessions, scope_fields=scope_fields)
        self._resource_model = resource_model
        self.resources: dict[str, Resource] = self._state.resources

    def list_resources(self, where: Mapping[str, Any] | None = None) -> dict[str, Resource]:
        from sqlmodel import select

        filters = self._build_filters(self._sqla_models.Resource, where)
        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.Resource).where(*filters)).all()
            result: dict[str, Resource] = {}
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                res = self._cache_resource(row)
                result[res.id] = res
        return result

    def create_resource(
        self,
        *,
        url: str,
        modality: str,
        local_path: str,
        caption: str | None,
        embedding: list[float] | None,
        user_data: dict[str, Any],
    ) -> Resource:
        res = self._resource_model(
            url=url,
            modality=modality,
            local_path=local_path,
            caption=caption,
            embedding=self._prepare_embedding(embedding),
            **user_data,
            created_at=self._now(),
            updated_at=self._now(),
        )

        with self._sessions.session() as session:
            session.add(res)
            session.commit()
            session.refresh(res)

        return self._cache_resource(res)

    def load_existing(self) -> None:
        from sqlmodel import select

        with self._sessions.session() as session:
            rows = session.scalars(select(self._sqla_models.Resource)).all()
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                self._cache_resource(row)

    def _cache_resource(self, res: Resource) -> Resource:
        self.resources[res.id] = res
        return res


__all__ = ["PostgresResourceRepo"]
