"""SQLite recall file repository implementation."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from sqlmodel import delete, select

from memu.database.models import RecallFile
from memu.database.repositories.recall_file import RecallFileRepo
from memu.database.sqlite.repositories.base import SQLiteRepoBase
from memu.database.sqlite.schema import SQLiteSQLAModels
from memu.database.sqlite.session import SQLiteSessionManager
from memu.database.state import DatabaseState

logger = logging.getLogger(__name__)


class SQLiteRecallFileRepo(SQLiteRepoBase, RecallFileRepo):
    """SQLite implementation of the recall file repository."""

    def __init__(
        self,
        *,
        state: DatabaseState,
        recall_file_model: type[Any],
        sqla_models: SQLiteSQLAModels,
        sessions: SQLiteSessionManager,
        scope_fields: list[str],
    ) -> None:
        """Initialize the recall file repository.

        Args:
            state: Shared database state for caching.
            recall_file_model: SQLModel class for recall files.
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
        self._recall_file_model = recall_file_model
        self.recall_files = self._state.recall_files

    def list_recall_files(self, where: Mapping[str, Any] | None = None) -> dict[str, RecallFile]:
        """List recall files matching the where clause.

        Args:
            where: Optional filter conditions.

        Returns:
            Dictionary of recall file ID to RecallFile mapping.
        """
        with self._sessions.session() as session:
            stmt = select(self._recall_file_model)
            filters = self._build_filters(self._recall_file_model, where)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.exec(stmt).all()

        result: dict[str, RecallFile] = {}
        for row in rows:
            recall_file = RecallFile(
                id=row.id,
                name=row.name,
                description=row.description,
                embedding=self._normalize_embedding(row.embedding),
                content=row.content,
                track=row.track,
                created_at=row.created_at,
                updated_at=row.updated_at,
                **self._scope_kwargs_from(row),
            )
            result[row.id] = recall_file
            self.recall_files[row.id] = recall_file

        return result

    def clear_recall_files(self, where: Mapping[str, Any] | None = None) -> dict[str, RecallFile]:
        """Clear recall files matching the where clause.

        Args:
            where: Optional filter conditions.

        Returns:
            Dictionary of deleted recall file ID to RecallFile mapping.
        """
        filters = self._build_filters(self._recall_file_model, where)
        with self._sessions.session() as session:
            # First get the objects to delete
            stmt = select(self._recall_file_model)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.exec(stmt).all()

            deleted: dict[str, RecallFile] = {}
            for row in rows:
                recall_file = RecallFile(
                    id=row.id,
                    name=row.name,
                    description=row.description,
                    embedding=self._normalize_embedding(row.embedding),
                    content=row.content,
                    track=row.track,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    **self._scope_kwargs_from(row),
                )
                deleted[row.id] = recall_file

            if not deleted:
                return {}

            # Delete from database
            del_stmt = delete(self._recall_file_model)
            if filters:
                del_stmt = del_stmt.where(*filters)
            session.exec(del_stmt)
            session.commit()

            # Clean up cache
            for recall_file_id in deleted:
                self.recall_files.pop(recall_file_id, None)

        return deleted

    def get_or_create_recall_file(
        self,
        *,
        name: str,
        description: str,
        embedding: list[float],
        user_data: dict[str, Any],
        track: str = "memory",
    ) -> RecallFile:
        """Get existing recall file by (name, track, scope) or create a new one.

        Args:
            name: Recall file name.
            description: Recall file description.
            embedding: Embedding vector.
            user_data: User scope data.
            track: Which track the file belongs to ("memory" or "skill").

        Returns:
            Existing or newly created RecallFile.
        """
        # Check for existing file with same name, track, and scope
        where: dict[str, Any] = {"name": name, "track": track, **user_data}
        with self._sessions.session() as session:
            stmt = select(self._recall_file_model)
            filters = self._build_filters(self._recall_file_model, where)
            if filters:
                stmt = stmt.where(*filters)
            existing = session.exec(stmt).first()

            if existing:
                recall_file = RecallFile(
                    id=existing.id,
                    name=existing.name,
                    description=existing.description,
                    embedding=self._normalize_embedding(existing.embedding),
                    content=existing.content,
                    track=existing.track,
                    created_at=existing.created_at,
                    updated_at=existing.updated_at,
                    **self._scope_kwargs_from(existing),
                )
                self.recall_files[existing.id] = recall_file
                return recall_file

            # Create new file
            now = self._now()
            row = self._recall_file_model(
                name=name,
                description=description,
                embedding=self._prepare_embedding(embedding),
                content=None,
                track=track,
                created_at=now,
                updated_at=now,
                **user_data,
            )
            session.add(row)
            session.commit()
            session.refresh(row)

        recall_file = RecallFile(
            id=row.id,
            name=row.name,
            description=row.description,
            embedding=embedding,
            content=None,
            track=track,
            created_at=row.created_at,
            updated_at=row.updated_at,
            **user_data,
        )
        self.recall_files[row.id] = recall_file
        return recall_file

    def update_recall_file(
        self,
        *,
        recall_file_id: str,
        name: str | None = None,
        description: str | None = None,
        embedding: list[float] | None = None,
        content: str | None = None,
    ) -> RecallFile:
        """Update an existing recall file.

        Args:
            recall_file_id: ID of recall file to update.
            name: New name (optional).
            description: New description (optional).
            embedding: New embedding vector (optional).
            content: New content text (optional).

        Returns:
            Updated RecallFile object.

        Raises:
            KeyError: If recall file not found.
        """
        with self._sessions.session() as session:
            stmt = select(self._recall_file_model).where(self._recall_file_model.id == recall_file_id)
            row = session.exec(stmt).first()

            if row is None:
                msg = f"RecallFile with id {recall_file_id} not found"
                raise KeyError(msg)

            if name is not None:
                row.name = name
            if description is not None:
                row.description = description
            if embedding is not None:
                row.embedding = self._prepare_embedding(embedding)
            if content is not None:
                row.content = content
            row.updated_at = self._now()

            session.add(row)
            session.commit()
            session.refresh(row)

        recall_file = RecallFile(
            id=row.id,
            name=row.name,
            description=row.description,
            embedding=self._normalize_embedding(row.embedding),
            content=row.content,
            track=row.track,
            created_at=row.created_at,
            updated_at=row.updated_at,
            **self._scope_kwargs_from(row),
        )
        self.recall_files[row.id] = recall_file
        return recall_file

    def load_existing(self) -> None:
        """Load all existing recall files from database into cache."""
        self.list_recall_files()


__all__ = ["SQLiteRecallFileRepo"]
