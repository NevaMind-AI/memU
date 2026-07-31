"""Unit test verifying recall file segment repositories do not duplicate segment objects in cache."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock

import pytest

from memu.app.settings import DatabaseConfig, DefaultUserModel
from memu.database.factory import build_database
from memu.database.interfaces import Database


@pytest.fixture(params=["inmemory", "sqlite"])
def db_backend(request: pytest.FixtureRequest, tmp_path: Any) -> Database:
    if request.param == "inmemory":
        config = DatabaseConfig.model_validate({"metadata_store": {"provider": "inmemory"}})
    else:
        config = DatabaseConfig.model_validate({
            "metadata_store": {"provider": "sqlite", "dsn": f"sqlite:///{tmp_path}/memu.sqlite3"}
        })
    return build_database(config=config, user_model=DefaultUserModel)


def test_list_segments_no_duplicates_in_cache(db_backend: Database) -> None:
    """Test inmemory and sqlite backends do not duplicate segment objects in cache."""
    f = db_backend.recall_file_repo.get_or_create_recall_file(
        name="file1", description="desc", embedding=[0.1], user_data={"user_id": "u1"}
    )
    db_backend.recall_file_segment_repo.create_segment(
        recall_file_id=f.id, text="seg1", embedding=[0.1], user_data={"user_id": "u1"}
    )

    db_backend.recall_file_segment_repo.list_segments()
    db_backend.recall_file_segment_repo.list_segments()
    db_backend.recall_file_segment_repo.list_segments()

    assert len(db_backend.recall_file_segment_repo.segments) == 1


class StubSession:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalars(self, stmt: Any) -> StubSession:
        return self

    def all(self) -> list[Any]:
        return self._rows


class StubSessionManager:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    @contextmanager
    def session(self):
        yield StubSession(self._rows)


def test_postgres_list_segments_deduplicates_cache() -> None:
    """Test PostgresRecallFileSegmentRepo list_segments deduplication logic directly with a stub session."""
    pytest.importorskip("pgvector")

    from memu.database.postgres.models import RecallFileSegment as SQLARecallFileSegment
    from memu.database.postgres.repositories.recall_file_segment_repo import PostgresRecallFileSegmentRepo
    from memu.database.postgres.schema import SQLAModels
    from memu.database.state import DatabaseState

    state = DatabaseState()
    sqla_models = SQLAModels(
        Resource=MagicMock(),
        RecallFile=MagicMock(),
        RecallFileSegment=SQLARecallFileSegment,
    )

    row1 = MagicMock()
    row1.id = "seg-1"
    row1.recall_file_id = "file-1"
    row1.track = "memory"
    row1.text = "text 1"
    row1.embedding = [0.1, 0.2]
    row1.created_at = None
    row1.updated_at = None

    row2 = MagicMock()
    row2.id = "seg-2"
    row2.recall_file_id = "file-1"
    row2.track = "memory"
    row2.text = "text 2"
    row2.embedding = [0.3, 0.4]
    row2.created_at = None
    row2.updated_at = None

    canned_rows = [row1, row2]
    sessions = StubSessionManager(canned_rows)

    repo = PostgresRecallFileSegmentRepo(
        state=state,
        recall_file_segment_model=MagicMock(),
        sqla_models=sqla_models,
        sessions=sessions,  # type: ignore[arg-type]
        scope_fields=[],
    )

    # Calling list_segments 3 times should return 2 rows each time,
    # and keep the cache size at 2 (2 -> 2 -> 2) instead of growing (2 -> 4 -> 6).
    res1 = repo.list_segments()
    res2 = repo.list_segments()
    res3 = repo.list_segments()

    assert len(res1) == 2
    assert len(res2) == 2
    assert len(res3) == 2
    assert len(repo.segments) == 2
    assert [s.id for s in repo.segments] == ["seg-1", "seg-2"]
