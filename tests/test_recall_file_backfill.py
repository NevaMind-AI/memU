"""Backfill parity for ``get_or_create_recall_file`` across storage backends (memU#608).

When the method matches an existing row by its domain identity it must top up a stub that
was persisted with an empty description or embedding — nothing else will, because the only
other writer, ``update_recall_file``, skips ``None`` arguments, so an empty field stays
empty for good.

The backends had drifted: SQLite carried no backfill at all, and SQLite and Postgres both
tested ``is None``, which never fires for the empties the models actually hold (``description``
is NOT NULL so it stubs as ``""``, and an embedding stubs as ``[]``). These tests pin the
shared contract for every backend that runs without a server, so the implementations cannot
drift apart again. Postgres needs a live server and stays covered by inspection.
"""

from __future__ import annotations

import itertools
import pathlib

import pendulum
import pytest

from memu.app.settings import DatabaseConfig, DefaultUserModel
from memu.database.factory import build_database
from memu.database.repositories.recall_file import RecallFileRepo

BACKENDS = ["inmemory", "sqlite"]
USER_DATA = {"user_id": "user123"}
EMBEDDING = [0.12, 0.34, 0.56, 0.78]
DESCRIPTION = "User profile memory document"


@pytest.fixture(autouse=True)
def _monotonic_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tick ``pendulum.now`` one second per call so timestamp assertions are exact.

    Both backends and ``BaseRecord``'s default factory resolve ``pendulum.now`` at call
    time, so patching the module attribute covers create and backfill alike. The real
    clock is too coarse for this: an in-memory create and the backfill that follows it
    land on the same microsecond, which would make "updated_at advanced" flaky.
    """
    start = pendulum.datetime(2026, 1, 1, tz="UTC")
    ticks = itertools.count()
    monkeypatch.setattr(pendulum, "now", lambda tz=None: start.add(seconds=next(ticks)))


def _repo(provider: str, tmp_path: pathlib.Path) -> RecallFileRepo:
    """A recall file repository for ``provider``, backed by ``tmp_path`` when on disk."""
    metadata_store: dict[str, str] = {"provider": provider}
    if provider == "sqlite":
        metadata_store["dsn"] = f"sqlite:///{tmp_path / 'parity.sqlite3'}"
    config = DatabaseConfig.model_validate({"metadata_store": metadata_store})
    return build_database(config=config, user_model=DefaultUserModel).recall_file_repo


def _get_or_create(repo: RecallFileRepo, *, description: str, embedding: list[float]) -> object:
    return repo.get_or_create_recall_file(
        name="profile-doc",
        description=description,
        embedding=embedding,
        user_data=USER_DATA,
        track="memory",
    )


@pytest.mark.parametrize("provider", BACKENDS)
def test_backfills_stub_description_and_embedding(provider: str, tmp_path: pathlib.Path) -> None:
    repo = _repo(provider, tmp_path)
    stub = _get_or_create(repo, description="", embedding=[])
    stubbed_at = stub.updated_at

    matched = _get_or_create(repo, description=DESCRIPTION, embedding=EMBEDDING)

    assert matched.id == stub.id, "must match the existing row, not insert a second one"
    assert matched.description == DESCRIPTION
    assert matched.embedding == EMBEDDING
    assert matched.updated_at > stubbed_at


@pytest.mark.parametrize("provider", BACKENDS)
def test_backfill_survives_a_reread(provider: str, tmp_path: pathlib.Path) -> None:
    # The backfill has to be persisted, not just patched onto the returned copy: the
    # SQLite path builds its ``RecallFile`` from the row, so an unflushed update would
    # still read back correctly within the call but be lost to every later query.
    repo = _repo(provider, tmp_path)
    stub = _get_or_create(repo, description="", embedding=[])
    _get_or_create(repo, description=DESCRIPTION, embedding=EMBEDDING)

    reread = repo.list_recall_files(where={**USER_DATA, "track": "memory"})[stub.id]

    assert reread.description == DESCRIPTION
    assert reread.embedding == EMBEDDING


@pytest.mark.parametrize("provider", BACKENDS)
def test_populated_fields_are_never_overwritten(provider: str, tmp_path: pathlib.Path) -> None:
    # Backfill tops up empties; it is not an update. Overwriting here would silently
    # clobber a description the caller never meant to change — that is what
    # ``update_recall_file`` is for.
    repo = _repo(provider, tmp_path)
    created = _get_or_create(repo, description=DESCRIPTION, embedding=EMBEDDING)

    matched = _get_or_create(repo, description="something else", embedding=[0.9, 0.9])

    assert matched.description == DESCRIPTION
    assert matched.embedding == EMBEDDING
    assert matched.updated_at == created.updated_at, "an unchanged row must not be touched"


@pytest.mark.parametrize("provider", BACKENDS)
def test_empty_caller_values_leave_a_stub_alone(provider: str, tmp_path: pathlib.Path) -> None:
    # Nothing better to write, so nothing is written: the row keeps its empties and
    # updated_at does not move. Guards against a write-always backfill that bumps the
    # timestamp on every commit that happens to carry no description.
    repo = _repo(provider, tmp_path)
    stub = _get_or_create(repo, description="", embedding=[])
    stubbed_at = stub.updated_at

    matched = _get_or_create(repo, description="", embedding=[])

    assert matched.description == ""
    assert not matched.embedding
    assert matched.updated_at == stubbed_at
