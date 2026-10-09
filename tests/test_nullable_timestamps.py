"""Unit tests for BaseRecord nullable datetime fields (issue #8 fix).

When records are deserialized from external sources (databases, APIs, JSON),
``created_at`` and ``updated_at`` may be ``None``.  Previously this raised a
``pydantic.ValidationError`` because the fields were typed as ``datetime``
(non-nullable).  After the fix they accept ``None`` gracefully while still
auto-populating with ``pendulum.now("UTC")`` for freshly created objects.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from memu.database.models import BaseRecord, CategoryItem, MemoryCategory, MemoryItem, Resource


class TestBaseRecordNullableDatetime:
    """Verify that ``created_at`` and ``updated_at`` accept ``None``."""

    def test_default_factory_populates_datetime(self):
        """Freshly created records should still get auto-populated timestamps."""
        record = BaseRecord()
        assert isinstance(record.created_at, datetime)
        assert isinstance(record.updated_at, datetime)

    def test_explicit_none_accepted(self):
        """Passing ``None`` explicitly must not raise a ValidationError."""
        record = BaseRecord(created_at=None, updated_at=None)
        assert record.created_at is None
        assert record.updated_at is None

    def test_partial_none_accepted(self):
        """One field ``None``, the other auto-populated — both valid."""
        record = BaseRecord(created_at=None)
        assert record.created_at is None
        assert isinstance(record.updated_at, datetime)

    def test_memory_item_with_none_timestamps(self):
        """MemoryItem inherits BaseRecord; should tolerate ``None`` timestamps."""
        item = MemoryItem(
            resource_id=None,
            memory_type="knowledge",
            summary="test memory",
            created_at=None,
            updated_at=None,
        )
        assert item.created_at is None
        assert item.updated_at is None

    def test_memory_category_with_none_timestamps(self):
        """MemoryCategory inherits BaseRecord; should tolerate ``None`` timestamps."""
        cat = MemoryCategory(
            name="test",
            description="test category",
            created_at=None,
            updated_at=None,
        )
        assert cat.created_at is None

    def test_resource_with_none_timestamps(self):
        """Resource inherits BaseRecord; should tolerate ``None`` timestamps."""
        res = Resource(
            url="https://example.com",
            modality="text",
            local_path="/tmp/file.txt",
            created_at=None,
            updated_at=None,
        )
        assert res.created_at is None

    def test_category_item_with_none_timestamps(self):
        """CategoryItem inherits BaseRecord; should tolerate ``None`` timestamps."""
        ci = CategoryItem(
            item_id="item-1",
            category_id="cat-1",
            created_at=None,
            updated_at=None,
        )
        assert ci.created_at is None

    def test_model_dump_includes_none(self):
        """Serialized output should faithfully represent ``None`` values."""
        record = BaseRecord(created_at=None, updated_at=None)
        data = record.model_dump()
        assert data["created_at"] is None
        assert data["updated_at"] is None

    def test_model_validate_with_none(self):
        """``model_validate`` from raw dict with ``None`` timestamps must work."""
        data = {
            "id": "abc-123",
            "created_at": None,
            "updated_at": None,
        }
        record = BaseRecord.model_validate(data)
        assert record.id == "abc-123"
        assert record.created_at is None
        assert record.updated_at is None
