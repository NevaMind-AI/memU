"""SQLite resource repository implementation."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from sqlmodel import delete, select

from memu.database.models import Resource
from memu.database.repositories.resource import ResourceRepo
from memu.database.sqlite.repositories.base import SQLiteRepoBase
from memu.database.sqlite.schema import SQLiteSQLAModels
from memu.database.sqlite.session import SQLiteSessionManager
from memu.database.state import DatabaseState

logger = logging.getLogger(__name__)


class SQLiteResourceRepo(SQLiteRepoBase, ResourceRepo):
    """SQLite implementation of resource repository."""

    def __init__(
        self,
        *,
        state: DatabaseState,
        resource_model: type[Any],
        sqla_models: SQLiteSQLAModels,
        sessions: SQLiteSessionManager,
        scope_fields: list[str],
    ) -> None:
        """Initialize resource repository.

        Args:
            state: Shared database state for caching.
            resource_model: SQLModel class for resources.
            sqla_models: SQLAlchemy model container.
            sessions: Session manager for database connections.
            scope_fields: List of user scope field names.
        """
        super().__init__(
            state=state,
            sqla_models=sqla_models,
            sessions=sessions,
            scope_fields=scope_fields,
        )
        self._resource_model = resource_model
        self.resources = self._state.resources

    def list_resources(self, where: Mapping[str, Any] | None = None) -> dict[str, Resource]:
        """List resources matching the where clause.

        Args:
            where: Optional filter conditions.

        Returns:
            Dictionary of resource ID to Resource mapping.
        """
        # Prefer cached data if available and no filter
        if not where and self.resources:
            return dict(self.resources)

        with self._sessions.session() as session:
            stmt = select(self._resource_model)
            filters = self._build_filters(self._resource_model, where)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.exec(stmt).all()

        result: dict[str, Resource] = {}
        for row in rows:
            res = Resource(
                id=row.id,
                url=row.url,
                modality=row.modality,
                local_path=row.local_path,
                caption=row.caption,
                embedding=self._normalize_embedding(row.embedding_json),
                created_at=row.created_at,
                updated_at=row.updated_at,
                **self._scope_kwargs_from(row),
            )
            result[row.id] = res
            self.resources[row.id] = res

        return result

    def clear_resources(self, where: Mapping[str, Any] | None = None) -> dict[str, Resource]:
        """Clear resources matching the where clause.

        Args:
            where: Optional filter conditions.

        Returns:
            Dictionary of deleted resource ID to Resource mapping.
        """
        filters = self._build_filters(self._resource_model, where)
        with self._sessions.session() as session:
            # First get the objects to delete
            stmt = select(self._resource_model)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.exec(stmt).all()

            deleted: dict[str, Resource] = {}
            for row in rows:
                res = Resource(
                    id=row.id,
                    url=row.url,
                    modality=row.modality,
                    local_path=row.local_path,
                    caption=row.caption,
                    embedding=self._normalize_embedding(row.embedding_json),
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    **self._scope_kwargs_from(row),
                )
                deleted[row.id] = res

            if not deleted:
                return {}

            # Delete from database
            del_stmt = delete(self._resource_model)
            if filters:
                del_stmt = del_stmt.where(*filters)
            session.exec(del_stmt)
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
        """Create a new resource record.

        Args:
            url: Resource URL.
            modality: Resource modality type.
            local_path: Local file path.
            caption: Optional caption text.
            embedding: Optional embedding vector.
            user_data: User scope data.

        Returns:
            Created Resource object.
        """
        now = self._now()
        row = self._resource_model(
            url=url,
            modality=modality,
            local_path=local_path,
            caption=caption,
            embedding_json=self._prepare_embedding(embedding),
            created_at=now,
            updated_at=now,
            **user_data,
        )
        with self._sessions.session() as session:
            session.add(row)
            session.commit()
            session.refresh(row)

        res = Resource(
            id=row.id,
            url=row.url,
            modality=row.modality,
            local_path=row.local_path,
            caption=row.caption,
            embedding=embedding,
            created_at=row.created_at,
            updated_at=row.updated_at,
            **user_data,
        )
        self.resources[row.id] = res
        return res

    def load_existing(self) -> None:
        """Load all existing resources from database into cache."""
        self.list_resources()


__all__ = ["SQLiteResourceRepo"]
