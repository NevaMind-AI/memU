from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from memu.database.models import MARKDOWN_MODALITY, Resource
from memu.database.postgres.repositories.base import PostgresRepoBase
from memu.database.postgres.session import SessionManager
from memu.database.repositories.resource import ResourceRepo
from memu.database.state import DatabaseState
from memu.vector import cosine_topk


class PostgresResourceRepo(PostgresRepoBase, ResourceRepo):
    def __init__(
        self,
        *,
        state: DatabaseState,
        resource_model: type[Resource],
        sqla_models: Any,
        sessions: SessionManager,
        scope_fields: list[str],
        use_vector: bool = True,
    ) -> None:
        super().__init__(
            state=state, sqla_models=sqla_models, sessions=sessions, scope_fields=scope_fields, use_vector=use_vector
        )
        self._resource_model = resource_model
        self.resources: dict[str, Resource] = self._state.resources

    def get_resource(self, resource_id: str) -> Resource | None:
        from sqlmodel import select

        with self._sessions.session() as session:
            row = session.scalar(select(self._sqla_models.Resource).where(self._sqla_models.Resource.id == resource_id))
            if row:
                row.embedding = self._normalize_embedding(row.embedding)
                return self._cache_resource(row)
        return None

    def list_resources(self, where: Mapping[str, Any] | None = None, *, lane: str | None = None) -> dict[str, Resource]:
        from sqlmodel import select

        model = self._sqla_models.Resource
        filters = self._build_filters(model, where)
        if lane is not None:
            filters.append(model.lane == lane)
        with self._sessions.session() as session:
            rows = session.scalars(select(model).where(*filters)).all()
            result: dict[str, Resource] = {}
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                res = self._cache_resource(row)
                result[res.id] = res
        return result

    def clear_resources(
        self, where: Mapping[str, Any] | None = None, *, lane: str | None = None
    ) -> dict[str, Resource]:
        from sqlmodel import delete, select

        model = self._sqla_models.Resource
        filters = self._build_filters(model, where)
        if lane is not None:
            filters.append(model.lane == lane)
        with self._sessions.session() as session:
            rows = session.scalars(select(model).where(*filters)).all()
            deleted: dict[str, Resource] = {}
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                deleted[row.id] = row

            if not deleted:
                return {}

            session.exec(delete(model).where(*filters))
            session.commit()

            for res_id in deleted:
                self.resources.pop(res_id, None)

        return deleted

    def delete_resource(self, resource_id: str) -> None:
        from sqlmodel import delete

        with self._sessions.session() as session:
            session.exec(delete(self._sqla_models.Resource).where(self._sqla_models.Resource.id == resource_id))
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
        res = self._resource_model(
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
            **user_data,
            created_at=self._now(),
            updated_at=self._now(),
        )

        with self._sessions.session() as session:
            session.add(res)
            session.commit()
            session.refresh(res)

        res.embedding = self._normalize_embedding(res.embedding)
        return self._cache_resource(res)

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
        from sqlmodel import select

        model = self._sqla_models.Resource
        now = self._now()
        with self._sessions.session() as session:
            filters = [model.lane == lane, model.title == title]
            for key, value in user_data.items():
                filters.append(getattr(model, key) == value)
            existing = session.scalar(select(model).where(*filters))

            if existing:
                updated = False
                if getattr(existing, "embedding", None) is None:
                    existing.embedding = self._prepare_embedding(embedding)
                    updated = True
                if not getattr(existing, "description", None):
                    existing.description = description
                    updated = True
                if updated:
                    existing.updated_at = now
                    session.add(existing)
                    session.commit()
                    session.refresh(existing)
                existing.embedding = self._normalize_embedding(existing.embedding)
                return self._cache_resource(existing)

            res = self._resource_model(
                lane=lane,
                modality=MARKDOWN_MODALITY,
                title=title,
                slug=slug,
                description=description,
                embedding=self._prepare_embedding(embedding),
                created_at=now,
                updated_at=now,
                **user_data,
            )
            session.add(res)
            session.commit()
            session.refresh(res)

        res.embedding = self._normalize_embedding(res.embedding)
        return self._cache_resource(res)

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
        from sqlmodel import select

        model = self._sqla_models.Resource
        now = self._now()
        with self._sessions.session() as session:
            res = session.scalar(select(model).where(model.id == resource_id))
            if res is None:
                msg = f"Resource with id {resource_id} not found"
                raise KeyError(msg)

            if title is not None:
                res.title = title
            if description is not None:
                res.description = description
            if content is not None:
                res.content = content
            if summary is not None:
                res.summary = summary
            if embedding is not None:
                res.embedding = self._prepare_embedding(embedding)
            if resource_refs is not None:
                res.resource_refs = resource_refs

            res.updated_at = now
            session.add(res)
            session.commit()
            session.refresh(res)
            res.embedding = self._normalize_embedding(res.embedding)

        return self._cache_resource(res)

    def vector_search_resources(
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
        *,
        lane: str | None = None,
    ) -> list[tuple[str, float]]:
        """Rank resources by cosine similarity over stored embeddings.

        Uses pgvector ``cosine_distance`` when available, otherwise falls back to
        scoring the loaded resources in Python.
        """
        if not self._use_vector:
            return self._vector_search_local(query_vec, top_k, where=where, lane=lane)

        from sqlmodel import select

        model = self._sqla_models.Resource
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
            rows = session.scalars(select(self._sqla_models.Resource)).all()
            for row in rows:
                row.embedding = self._normalize_embedding(row.embedding)
                self._cache_resource(row)

    def _vector_search_local(
        self,
        query_vec: list[float],
        top_k: int,
        where: Mapping[str, Any] | None = None,
        *,
        lane: str | None = None,
    ) -> list[tuple[str, float]]:
        pool = self.list_resources(where, lane=lane)
        corpus = [(rid, res.embedding) for rid, res in pool.items() if res.embedding]
        return cosine_topk(query_vec, corpus, k=top_k)

    def _cache_resource(self, res: Resource) -> Resource:
        self.resources[res.id] = res
        return res


__all__ = ["PostgresResourceRepo"]
