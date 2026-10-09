"""SQLite segment cache behavior and traversal cost against a real database."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from memu.app.settings import DefaultUserModel
from memu.database.models import RecallFileSegment
from memu.database.sqlite.sqlite import SQLiteStore


@pytest.fixture
def store(tmp_path: Path) -> Iterator[SQLiteStore]:
    db = SQLiteStore(dsn=f"sqlite:///{tmp_path.as_posix()}/memory.db", scope_model=DefaultUserModel)
    try:
        yield db
    finally:
        db.close()


def seed(store: SQLiteStore, count: int, *, user: str = "u1", track: str = "memory") -> list[RecallFileSegment]:
    file = store.recall_file_repo.get_or_create_recall_file(
        name=f"{user}-{track}",
        description="preferences",
        embedding=[1.0, 0.0],
        user_data={"user_id": user},
        track=track,
    )
    return [
        store.recall_file_segment_repo.create_segment(
            recall_file_id=file.id,
            text=f"preference {i}",
            embedding=[1.0, 0.0],
            user_data={"user_id": user},
            track=track,
        )
        for i in range(count)
    ]


class CountingCache(list[RecallFileSegment]):
    """Measure visited cache entries without relying on wall-clock thresholds."""

    visits = 0

    def __iter__(self) -> Iterator[RecallFileSegment]:
        for segment in super().__iter__():
            self.visits += 1
            yield segment


@pytest.mark.parametrize("warm", [False, True])
def test_list_segments_cache_traversal_is_linear(store: SQLiteStore, warm: bool) -> None:
    segments = seed(store, 64)
    cache = CountingCache(segments if warm else [])
    store._state.segments = store.segments = store.recall_file_segment_repo.segments = cache

    result = store.recall_file_segment_repo.list_segments()

    assert {seg.id for seg in result} == {seg.id for seg in segments}
    assert len(cache) == len(segments)
    # Allow a constant number of full passes, but no per-row scan of the cache.
    assert cache.visits <= 2 * len(segments)


def test_reads_keep_shared_cache_and_observe_other_instances(store: SQLiteStore) -> None:
    first = seed(store, 2)
    cache = store.segments
    other = SQLiteStore(dsn=store.dsn, scope_model=DefaultUserModel)
    try:
        added = seed(other, 1, user="u2", track="skill")
        repo = store.recall_file_segment_repo
        for _ in range(2):
            assert {seg.id for seg in repo.list_segments({"user_id": "u2", "track__in": ["skill"]})} == {added[0].id}
            assert {seg.id for seg in repo.list_segments({"user_id": "u1"})} == {seg.id for seg in first}
            assert repo.list_segments({"user_id": "missing"}) == []
        assert store.segments is store._state.segments is repo.segments is cache
        assert len(cache) == 3
        assert cache[0] is first[0]
        assert {seg.id for seg in cache} == {seg.id for seg in first + added}
    finally:
        other.close()


@pytest.mark.parametrize("deletion", ["single", "file", "scope"])
def test_cache_reads_after_delete_and_create(store: SQLiteStore, deletion: str) -> None:
    removed = seed(store, 1)
    kept = seed(store, 1, user="u2")
    repo = store.recall_file_segment_repo
    cache = store.segments
    repo.list_segments()
    if deletion == "single":
        repo.delete_segment(removed[0].id)
    elif deletion == "file":
        repo.delete_segments_for_file(removed[0].recall_file_id)
    else:
        repo.clear_segments({"user_id": "u1"})
    added = seed(store, 1)
    expected = {seg.id for seg in kept + added}
    for _ in range(2):
        assert {seg.id for seg in repo.list_segments()} == expected
        assert {seg.id for seg in cache} == expected
        assert len(cache) == 2
    assert store.segments is store._state.segments is repo.segments is cache
