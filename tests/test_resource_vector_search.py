"""Resource search returns scoped records and cosine scores in ranked order."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from memu.app.settings import DatabaseConfig, DefaultUserModel
from memu.database.factory import build_database
from memu.database.interfaces import Database
from memu.database.models import Resource


@pytest.fixture(params=["inmemory", "sqlite"])
def db_backend(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[Database]:
    config = DatabaseConfig.model_validate({
        "metadata_store": {
            "provider": request.param,
            **({"dsn": f"sqlite:///{tmp_path}/resources.sqlite3"} if request.param == "sqlite" else {}),
        }
    })
    database = build_database(config=config, user_model=DefaultUserModel)
    try:
        yield database
    finally:
        database.close()


def _resource(
    database: Database,
    caption: str,
    embedding: list[float] | None,
    *,
    user_id: str = "u1",
    agent_id: str = "a1",
    track: str = "workspace",
) -> Resource:
    path = f"/synthetic/{caption}.md"
    return database.resource_repo.create_resource(
        url=path,
        local_path=path,
        caption=caption,
        embedding=embedding,
        user_data={"user_id": user_id, "agent_id": agent_id},
        track=track,
    )


def test_returns_resource_records_best_first(db_backend: Database) -> None:
    east = _resource(db_backend, "east", [1.0, 0.0])
    north = _resource(db_backend, "north", [0.0, 1.0])

    hits = db_backend.resource_repo.vector_search_resources([1.0, 0.0], 5)

    assert [resource.id for resource, _ in hits] == [east.id, north.id]
    assert [resource.caption for resource, _ in hits] == ["east", "north"]
    assert hits[0][0].url == east.url
    assert hits[0][0].local_path == east.local_path
    assert hits[0][1] == pytest.approx(1.0, abs=1e-6)
    assert hits[1][1] == pytest.approx(0.0)


@pytest.mark.parametrize("top_k, expected", [(1, ["east"]), (0, []), (-1, [])])
def test_respects_top_k(db_backend: Database, top_k: int, expected: list[str]) -> None:
    _resource(db_backend, "east", [1.0, 0.0])
    _resource(db_backend, "north", [0.0, 1.0])

    hits = db_backend.resource_repo.vector_search_resources([1.0, 0.0], top_k)

    assert [resource.caption for resource, _ in hits] == expected


def test_empty_store_returns_no_hits(db_backend: Database) -> None:
    assert db_backend.resource_repo.vector_search_resources([1.0, 0.0], 5) == []


@pytest.mark.parametrize(
    "embedding",
    [None, [], [1.0], [float("nan"), 0.0], [float("inf"), 0.0], [1e39, 0.0]],
    ids=["missing", "empty", "wrong-dimension", "nan", "inf", "float32-overflow"],
)
def test_skips_unusable_embeddings(db_backend: Database, embedding: list[float] | None) -> None:
    _resource(db_backend, "unusable", embedding)
    _resource(db_backend, "east", [1.0, 0.0])

    hits = db_backend.resource_repo.vector_search_resources([1.0, 0.0], 5)

    assert [resource.caption for resource, _ in hits] == ["east"]
    assert hits[0][1] == pytest.approx(1.0, abs=1e-6)


def test_filters_user_agent_and_track_before_top_k(db_backend: Database) -> None:
    _resource(db_backend, "other-user", [1.0, 0.0], user_id="u2")
    _resource(db_backend, "other-agent", [1.0, 0.0], agent_id="a2")
    _resource(db_backend, "other-track", [1.0, 0.0], track="conversation")
    _resource(db_backend, "matching-scope", [0.0, 1.0])

    hits = db_backend.resource_repo.vector_search_resources(
        [1.0, 0.0], 1, where={"user_id": "u1", "agent_id": "a1", "track__in": ["workspace"]}
    )

    assert [resource.caption for resource, _ in hits] == ["matching-scope"]
    assert hits[0][1] == pytest.approx(0.0)
