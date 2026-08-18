"""``RecallFileSegmentRepo.vector_search_segments`` — the contract and its two paths.

Every backend inherits the protocol's Python scan; Postgres overrides it with
pgvector. Both owe the caller the same thing: ``(segment, score)`` pairs, best
first, score a cosine *similarity*. These tests pin the shared contract on the
backends the suite can run, then pin the pgvector override against a stub
session, since scoring in SQL is precisely what cannot be checked in Python.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from memu.app import MemoryService
from memu.app.settings import DatabaseConfig, DefaultUserModel
from memu.database.factory import build_database
from memu.database.interfaces import Database

USER = {"user_id": "u1"}


@pytest.fixture(params=["inmemory", "sqlite"])
def db_backend(request: pytest.FixtureRequest, tmp_path: Any) -> Database:
    if request.param == "inmemory":
        config = DatabaseConfig.model_validate({"metadata_store": {"provider": "inmemory"}})
    else:
        config = DatabaseConfig.model_validate({
            "metadata_store": {"provider": "sqlite", "dsn": f"sqlite:///{tmp_path}/memu.sqlite3"}
        })
    return build_database(config=config, user_model=DefaultUserModel)


def _seed(db: Database, segments: list[tuple[str, list[float] | None, str]]) -> None:
    """Create one file and hang ``(text, embedding, track)`` segments off it."""
    file = db.recall_file_repo.get_or_create_recall_file(
        name="file1", description="desc", embedding=[1.0, 0.0], user_data=dict(USER)
    )
    for text, embedding, track in segments:
        db.recall_file_segment_repo.create_segment(
            recall_file_id=file.id, text=text, embedding=embedding, user_data=dict(USER), track=track
        )


def test_returns_segments_best_first(db_backend: Database) -> None:
    _seed(db_backend, [("east", [1.0, 0.0], "memory"), ("north", [0.0, 1.0], "memory")])

    hits = db_backend.recall_file_segment_repo.vector_search_segments([1.0, 0.0], 2)

    # Segments, not ids: the caller needs ``recall_file_id``/``text`` off the hit.
    assert [seg.text for seg, _ in hits] == ["east", "north"]
    assert hits[0][1] == pytest.approx(1.0, abs=1e-3)
    assert hits[0][1] > hits[1][1]


def test_truncates_to_top_k(db_backend: Database) -> None:
    _seed(db_backend, [("east", [1.0, 0.0], "memory"), ("north", [0.0, 1.0], "memory")])

    hits = db_backend.recall_file_segment_repo.vector_search_segments([1.0, 0.0], 1)

    assert [seg.text for seg, _ in hits] == ["east"]


def test_nonpositive_top_k_returns_nothing(db_backend: Database) -> None:
    _seed(db_backend, [("east", [1.0, 0.0], "memory")])

    assert db_backend.recall_file_segment_repo.vector_search_segments([1.0, 0.0], 0) == []
    assert db_backend.recall_file_segment_repo.vector_search_segments([1.0, 0.0], -1) == []


def test_skips_segments_without_an_embedding(db_backend: Database) -> None:
    _seed(db_backend, [("unembedded", None, "memory"), ("east", [1.0, 0.0], "memory")])

    # top_k covers both, so an unembedded segment could only show up by being
    # ranked — it must be excluded outright, not sorted to the bottom.
    hits = db_backend.recall_file_segment_repo.vector_search_segments([1.0, 0.0], 5)

    assert [seg.text for seg, _ in hits] == ["east"]


def test_scopes_to_where_including_track_in(db_backend: Database) -> None:
    _seed(db_backend, [("east", [1.0, 0.0], "memory"), ("skill east", [1.0, 0.0], "skill")])

    hits = db_backend.recall_file_segment_repo.vector_search_segments(
        [1.0, 0.0], 5, where={**USER, "track__in": ["skill"]}
    )

    assert [seg.text for seg, _ in hits] == ["skill east"]


class _FakeEmbeddingClient:
    embed_model = "fake"

    async def embed(self, inputs: list[str]) -> tuple[list[list[float]], None]:
        return [[1.0 if "coffee" in text.lower() else 0.0, 0.0] for text in inputs], None


async def test_progressive_retrieve_takes_the_repo_shortcut() -> None:
    """The app layer must delegate ranking, not re-rank a pool of its own."""
    service = MemoryService(database_config={"metadata_store": {"provider": "inmemory"}})
    fake = _FakeEmbeddingClient()
    service._embedding_pool._cache["default"] = fake
    service._embedding_pool._cache["embedding"] = fake
    await service.commit_results(
        recall_files=[{"name": "Profile", "track": "memory", "description": "d", "content": "likes coffee\nlikes tea"}]
    )

    repo = service._get_database().recall_file_segment_repo
    native_calls: list[int] = []
    scans = 0
    real_list_segments = repo.list_segments

    def counting_list_segments(where: Any = None) -> Any:
        nonlocal scans
        scans += 1
        return real_list_segments(where)

    def native_search(query_vec: list[float], top_k: int, where: Any = None) -> Any:
        native_calls.append(top_k)
        # A backend-native answer the Python scan would never produce: one hit,
        # the *worse* match, at an impossible score.
        return [(next(seg for seg in real_list_segments(where) if seg.text == "likes tea"), 42.0)]

    repo.list_segments = counting_list_segments  # type: ignore[method-assign]
    repo.vector_search_segments = native_search  # type: ignore[method-assign]

    result = await service.progressive_retrieve("coffee")

    # The override's answer is what came back, verbatim — so nothing re-ranked it.
    assert native_calls == [service.progressive_retrieve_config.file.top_k]
    assert [seg["text"] for seg in result["segments"]] == ["likes tea"]
    assert result["segments"][0]["score"] == pytest.approx(42.0)
    # And no full-corpus scan happened behind the override's back.
    assert scans == 0


class _StubSession:
    """Captures the statement it is handed and replays canned rows."""

    def __init__(self, rows: list[Any], seen: list[Any]) -> None:
        self._rows = rows
        self._seen = seen

    def exec(self, stmt: Any) -> _StubSession:
        self._seen.append(stmt)
        return self

    def scalars(self, stmt: Any) -> _StubSession:
        self._seen.append(stmt)
        return self

    def all(self) -> list[Any]:
        return self._rows


class _StubSessionManager:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows
        self.seen: list[Any] = []

    @contextmanager
    def session(self) -> Any:
        yield _StubSession(self._rows, self.seen)


def _row(seg_id: str, text: str, embedding: list[float]) -> Any:
    row = MagicMock()
    row.id = seg_id
    row.recall_file_id = "file-1"
    row.track = "memory"
    row.text = text
    row.embedding = embedding
    row.created_at = row.updated_at = datetime(2026, 1, 1, tzinfo=UTC)
    return row


def _postgres_repo(rows: list[Any], *, use_vector: bool) -> tuple[Any, _StubSessionManager]:
    """A Postgres repo over a stub session, on the real ORM models.

    The models must be the real ones: ``embedding`` has to be an actual pgvector
    column for ``cosine_distance`` to compile, which is the half of this that a
    mock would quietly fake.
    """
    from memu.database.postgres.repositories.recall_file_segment_repo import PostgresRecallFileSegmentRepo
    from memu.database.postgres.schema import get_sqlalchemy_models
    from memu.database.state import DatabaseState

    sqla_models = get_sqlalchemy_models(scope_model=DefaultUserModel)
    sessions = _StubSessionManager(rows)
    repo = PostgresRecallFileSegmentRepo(
        state=DatabaseState(),
        recall_file_segment_model=sqla_models.RecallFileSegment,
        sqla_models=sqla_models,
        sessions=sessions,  # type: ignore[arg-type]
        scope_fields=[],
        use_vector=use_vector,
    )
    return repo, sessions


def test_postgres_ranks_and_truncates_in_sql() -> None:
    pytest.importorskip("pgvector")

    repo, sessions = _postgres_repo([(_row("seg-1", "east", [1.0, 0.0]), 0.25)], use_vector=True)

    hits = repo.vector_search_segments([1.0, 0.0], 3, where={"track__in": ["memory"]})

    sql = str(sessions.seen[0])
    assert "<=>" in sql  # ordered by pgvector's cosine operator...
    assert "LIMIT" in sql  # ...and truncated by the database, not by Python.
    assert "IS NOT NULL" in sql  # unembedded rows never enter the ranking
    # pgvector returns a distance; the contract is similarity, so 1 - 0.25.
    assert hits[0][0].text == "east"
    assert hits[0][1] == pytest.approx(0.75)


def test_postgres_caches_hits_like_a_listing() -> None:
    pytest.importorskip("pgvector")

    repo, _ = _postgres_repo([(_row("seg-1", "east", [1.0, 0.0]), 0.25)], use_vector=True)

    repo.vector_search_segments([1.0, 0.0], 3)

    assert [seg.id for seg in repo.segments] == ["seg-1"]


def test_postgres_native_path_honours_nonpositive_top_k() -> None:
    pytest.importorskip("pgvector")

    repo, sessions = _postgres_repo([], use_vector=True)

    # ``LIMIT 0``/``LIMIT -1`` is not a query worth sending.
    assert repo.vector_search_segments([1.0, 0.0], 0) == []
    assert sessions.seen == []
