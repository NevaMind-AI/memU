"""Shared base repository functionality for all database backends.

This module provides common methods used across SQLite and PostgreSQL repository
implementations to eliminate code duplication.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import pendulum

logger = logging.getLogger(__name__)


class RepoBaseMixin:
    """Shared repository methods for all database backends.

    This mixin provides common functionality used by both SQLite and PostgreSQL
    repository implementations, including:
    - Scope field extraction
    - Filter building for SQLAlchemy queries
    - In-memory where clause matching
    - Database commit operations
    - Timestamp generation
    """

    def _scope_kwargs_from(self, obj: Any) -> dict[str, Any]:
        """Extract scope fields from an object.

        Args:
            obj: Object to extract scope fields from.

        Returns:
            Dictionary mapping scope field names to their values.
        """
        return {field: getattr(obj, field, None) for field in self._scope_fields}

    def _build_filters(self, model: Any, where: Mapping[str, Any] | None) -> list[Any]:
        """Build SQLAlchemy filter expressions from where clause.

        Args:
            model: SQLAlchemy model class.
            where: Optional where clause with field mappings.

        Returns:
            List of SQLAlchemy filter expressions.

        Raises:
            ValueError: If an unknown filter field is specified.
        """
        if not where:
            return []
        filters: list[Any] = []
        for raw_key, expected in where.items():
            if expected is None:
                continue
            field, op = [*raw_key.split("__", 1), None][:2]
            column = getattr(model, str(field), None)
            if column is None:
                msg = f"Unknown filter field '{field}' for model '{model.__name__}'"
                raise ValueError(msg)
            if op == "in":
                if isinstance(expected, str):
                    filters.append(column == expected)
                else:
                    filters.append(column.in_(expected))
            else:
                filters.append(column == expected)
        return filters

    @staticmethod
    def _matches_where(obj: Any, where: Mapping[str, Any] | None) -> bool:
        """Check if object matches where clause (for in-memory filtering).

        Args:
            obj: Object to check.
            where: Optional where clause with field mappings.

        Returns:
            True if object matches the where clause, False otherwise.
        """
        if not where:
            return True
        for raw_key, expected in where.items():
            if expected is None:
                continue
            field, op = [*raw_key.split("__", 1), None][:2]
            actual = getattr(obj, str(field), None)
            if op == "in":
                if isinstance(expected, str):
                    if actual != expected:
                        return False
                else:
                    try:
                        if actual not in expected:
                            return False
                    except TypeError:
                        return False
            else:
                if actual != expected:
                    return False
        return True

    def _merge_and_commit(self, obj: Any) -> None:
        """Merge object into session and commit.

        Args:
            obj: Object to merge and commit.
        """
        with self._sessions.session() as session:
            session.merge(obj)
            session.commit()

    def _now(self) -> pendulum.DateTime:
        """Get current UTC time.

        Returns:
            Current UTC datetime as pendulum DateTime.
        """
        return pendulum.now("UTC")


__all__ = ["RepoBaseMixin"]
