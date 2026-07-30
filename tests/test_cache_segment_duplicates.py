"""Unit test verifying list_segments does not duplicate segment objects in cache."""

from __future__ import annotations

from typing import Any

import pytest

from memu.app.settings import DatabaseConfig, DefaultUserModel
from memu.database.factory import build_database
from memu.database.interfaces import Database


@pytest.fixture(params=["inmemory", "sqlite"])
def db_backend(request: pytest.FixtureRequest, tmp_path: Any) -> Database:
    if request.param == "inmemory":
        config = DatabaseConfig.model_validate({"metadata_store": {"provider": "inmemory"}})
    else:
        config = DatabaseConfig.model_validate(
            {"metadata_store": {"provider": "sqlite", "dsn": f"sqlite:///{tmp_path}/memu.sqlite3"}}
        )
    return build_database(config=config, user_model=DefaultUserModel)


def test_list_segments_no_duplicates_in_cache(db_backend: Database) -> None:
    # 1. Create a recall file and a segment
    f = db_backend.recall_file_repo.get_or_create_recall_file(
        name="file1", description="desc", embedding=[0.1], user_data={"user_id": "u1"}
    )
    db_backend.recall_file_segment_repo.create_segment(
        recall_file_id=f.id, text="seg1", embedding=[0.1], user_data={"user_id": "u1"}
    )

    # 2. Call list_segments multiple times
    db_backend.recall_file_segment_repo.list_segments()
    db_backend.recall_file_segment_repo.list_segments()
    db_backend.recall_file_segment_repo.list_segments()

    # 3. Cache must still contain only 1 segment
    assert len(db_backend.recall_file_segment_repo.segments) == 1
