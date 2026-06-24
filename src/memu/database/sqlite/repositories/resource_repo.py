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
from memu.vector import cosine_topk

logger = logging.getLogger(__name__)


class SQLiteResourceRepo(SQLiteRepoBase, ResourceRepo):
    """SQLite implementation of the resource repository.

    A single physical table holds both raw inputs (``lane="source"``) and the
    generated lane docs (``lane`` in {index, memory}).
    """

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

    def _row_to_resource(self, row: Any) -> Resource:
        """Map an ORM row to a backend-agnostic Resource record."""
        return Resource(
            id=row.id,
            lane=row.lane,
            modality=row.modality,
            url=row.url,
            local_path=row.local_path,
            slug=row.slug,
            title=row.title,
            description=row.description,
            content=row.content,
            summary=row.summary,
            embedding=self._normalize_embedding(row.embedding),
            resource_refs=row.resource_refs or [],
            created_at=row.created_at,
            updated_at=row.updated_at,
            **self._scope_kwargs_from(row),
        )

    def get_resource(self, resource_id: str) -> Resource | None:
        """Get a resource by ID."""
        if resource_id in self.resources:
            return self.resources[resource_id]

        with self._sessions.session() as session:
            stmt = select(self._resource_model).where(self._resource_model.id == resource_id)
            row = session.exec(stmt).first()

        if row is None:
            return None

        res = self._row_to_resource(row)
        self.resources[row.id] = res
        return res

    def list_resources(self, where: Mapping[str, Any] | None = None, *, lane: str | None = None) -> dict[str, Resource]:
        """List resources matching the where clause and optional lane filter."""
        filters = self._build_filters(self._resource_model, where)
        filters.extend(self._lane_filters(self._resource_model, lane))
        with self._sessions.session() as session:
            stmt = select(self._resource_model)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.exec(stmt).all()

        result: dict[str, Resource] = {}
        for row in rows:
            res = self._row_to_resource(row)
            result[row.id] = res
            self.resources[row.id] = res

        return result

    def clear_resources(
        self, where: Mapping[str, Any] | None = None, *, lane: str | None = None
    ) -> dict[str, Resource]:
        """Clear resources matching the where clause and optional lane filter."""
        filters = self._build_filters(self._resource_model, where)
        filters.extend(self._lane_filters(self._resource_model, lane))
        with self._sessions.session() as session:
            stmt = select(self._resource_model)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.exec(stmt).all()

            deleted: dict[str, Resource] = {row.id: self._row_to_resource(row) for row in rows}

            if not deleted:
                return {}

            del_stmt = delete(self._resource_model)
            if filters:
                del_stmt = del_stmt.where(*filters)
            session.exec(del_stmt)
            session.commit()

        for res_id in deleted:
            self.resources.pop(res_id, None)

        return deleted

    def delete_resource(self, resource_id: str) -> None:
        """Delete a single resource by id (used for cascade sync)."""
        with self._sessions.session() as session:
            session.exec(delete(self._resource_model).where(self._resource_model.id == resource_id))
            session.commit()
        self.resources.pop(resource_id, None)

    def create_resource(
        self,
        *,
        modality: str,
        user_data: dict[str, Any],
        lane: str = "source",
        url: str | None = None,
        local_path: str | None = None,
        slug: str | None = None,
        title: str | None = None,
        description: str | None = None,
        content: str | None = None,
        summary: str | None = None,
        embedding: list[float] | None = None,
        resource_refs: list[dict[str, Any]] | None = None,
    ) -> Resource:
        """Create a new resource record (raw input or generated lane doc)."""
        now = self._now()
        row = self._resource_model(
            lane=lane,
            modality=modality,
            url=url,
            local_path=local_path,
            slug=slug,
            title=title,
            description=description,
            content=content,
            summary=summary,
            embedding=self._prepare_embedding(embedding),
            resource_refs=resource_refs or [],
            created_at=now,
            updated_at=now,
            **user_data,
        )
        with self._sessions.session() as session:
            session.add(row)
            session.commit()
            session.refresh(row)

        res = self._row_to_resource(row)
        self.resources[row.id] = res
        return res

    def get_or_create_doc(
        self,
        *,
        lane: str,
        title: str,
        description: str,
        embedding: list[float],
        user_data: dict[str, Any],
        slug: str | None = None,
    ) -> Resource:
        """Get an existing generated doc by ``(lane, title, scope)`` or create one."""
        where: dict[str, Any] = {"lane": lane, "title": title, **user_data}
        filters = self._build_filters(self._resource_model, where)
        with self._sessions.session() as session:
            stmt = select(self._resource_model)
            if filters:
                stmt = stmt.where(*filters)
            existing = session.exec(stmt).first()

            if existing is not None:
                changed = False
                now = self._now()
                if self._normalize_embedding(existing.embedding) is None:
                    existing.embedding = self._prepare_embedding(embedding)
                    existing.updated_at = now
                    changed = True
                if not existing.description:
                    existing.description = description
                    existing.updated_at = now
                    changed = True
                if changed:
                    session.add(existing)
                    session.commit()
                    session.refresh(existing)
                res = self._row_to_resource(existing)
                self.resources[existing.id] = res
                return res

        return self.create_resource(
            modality="markdown",
            lane=lane,
            title=title,
            slug=slug,
            description=description,
            embedding=embedding,
            user_data=user_data,
        )

    def update_resource(
        self,
        *,
        resource_id: str,
        title: str | None = None,
        description: str | None = None,
        content: str | None = None,
        summary: str | None = None,
        embedding: list[float] | None = None,
        resource_refs: list[dict[str, Any]] | None = None,
    ) -> Resource:
        """Update mutable fields of an existing resource."""
        with self._sessions.session() as session:
            stmt = select(self._resource_model).where(self._resource_model.id == resource_id)
            row = session.exec(stmt).first()

            if row is None:
                msg = f"Resource with id {resource_id} not found"
                raise KeyError(msg)

            if title is not None:
                row.title = title
            if description is not None:
                row.description = description
            if content is not None:
                row.content = content
            if summary is not None:
                row.summary = summary
            if embedding is not None:
                row.embedding = self._prepare_embedding(embedding)
            if resource_refs is not None:
                row.resource_refs = resource_refs
            row.updated_at = self._now()

            session.add(row)
            session.commit()
            session.refresh(row)

        res = self._row_to_resource(row)
        self.resources[row.id] = res
        return res

    def vector_search_resources(
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
        *,
        lane: str | None = None,
    ) -> list[tuple[str, float]]:
        """Rank resources by brute-force cosine similarity of stored embeddings.

        SQLite has no native vector support, so embeddings are scored in Python.
        """
        pool = self.list_resources(where, lane=lane)
        corpus = [(rid, res.embedding) for rid, res in pool.items() if res.embedding]
        return cosine_topk(query_vec, corpus, k=top_k)

    def load_existing(self) -> None:
        """Load all existing resources from database into cache."""
        self.list_resources()


__all__ = ["SQLiteResourceRepo"]
