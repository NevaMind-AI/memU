from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from memu.database.models import Resource
from memu.database.postgres.repositories.base import PostgresRepoBase
from memu.database.postgres.session import AsyncSessionManager, SessionManager
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
        async_sessions: AsyncSessionManager | None = None,
        scope_fields: list[str],
    ) -> None:
        super().__init__(
            state=state,
            sqla_models=sqla_models,
            sessions=sessions,
            async_sessions=async_sessions,
            scope_fields=scope_fields,
        )
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

    def clear_resources(self, where: Mapping[str, Any] | None = None) -> dict[str, Resource]:
        from sqlmodel import delete, select

        filters = self._build_filters(self._sqla_models.Resource, where)
        with self._sessions.session() as session:
            # First get the objects to delete
            rows = session.scalars(select(self._sqla_models.Resource).where(*filters)).all()
            deleted: dict[str, Resource] = {}
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                deleted[row.id] = row

            if not deleted:
                return {}

            # Delete from database
            session.exec(delete(self._sqla_models.Resource).where(*filters))
            session.commit()

            # Clean up cache
            for res_id in deleted:
                self.resources.pop(res_id, None)

        return deleted

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

    async def list_resources_async(self, where: Mapping[str, Any] | None = None) -> dict[str, Resource]:
        if self._async_sessions is None:
            raise RuntimeError("Async sessions not initialized")
        from sqlalchemy import select

        filters = self._build_filters(self._sqla_models.Resource, where)
        async with self._async_sessions.session() as session:
            result = await session.execute(select(self._sqla_models.Resource).where(*filters))
            rows = result.scalars().all()
            result_dict: dict[str, Resource] = {}
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                res = self._cache_resource(row)
                result_dict[res.id] = res
        return result_dict

    async def clear_resources_async(self, where: Mapping[str, Any] | None = None) -> dict[str, Resource]:
        if self._async_sessions is None:
            raise RuntimeError("Async sessions not initialized")
        from sqlalchemy import delete, select

        filters = self._build_filters(self._sqla_models.Resource, where)
        async with self._async_sessions.session() as session:
            # First get the objects to delete
            result = await session.execute(select(self._sqla_models.Resource).where(*filters))
            rows = result.scalars().all()
            deleted: dict[str, Resource] = {}
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                deleted[row.id] = row

            if not deleted:
                return {}

            # Delete from database
            await session.execute(delete(self._sqla_models.Resource).where(*filters))
            await session.commit()

            # Clean up cache
            for res_id in deleted:
                self.resources.pop(res_id, None)

        return deleted

    async def create_resource_async(
        self,
        *,
        url: str,
        modality: str,
        local_path: str,
        caption: str | None,
        embedding: list[float] | None,
        user_data: dict[str, Any],
    ) -> Resource:
        if self._async_sessions is None:
            raise RuntimeError("Async sessions not initialized")
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

        async with self._async_sessions.session() as session:
            session.add(res)
            await session.commit()
            await session.refresh(res)

        return self._cache_resource(res)

    async def load_existing_async(self) -> None:
        if self._async_sessions is None:
            raise RuntimeError("Async sessions not initialized")
        from sqlalchemy import select

        async with self._async_sessions.session() as session:
            result = await session.execute(select(self._sqla_models.Resource))
            rows = result.scalars().all()
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                self._cache_resource(row)

    def _cache_resource(self, res: Resource) -> Resource:
        self.resources[res.id] = res
        return res


__all__ = ["PostgresResourceRepo"]
