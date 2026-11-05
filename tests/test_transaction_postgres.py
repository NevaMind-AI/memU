"""Optional integration checks against an isolated local PostgreSQL server."""

from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from sqlalchemy import create_engine, text

from memu.database.transaction import AtomicSessionManager


@pytest.fixture
def postgres_engine() -> Any:
    dsn = os.environ.get("MEMU_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("MEMU_TEST_POSTGRES_DSN not set")
    engine = create_engine(dsn)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS memu_transaction_test"))
        connection.execute(text("CREATE TABLE memu_transaction_test (id INTEGER PRIMARY KEY, value TEXT)"))
    yield engine
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE memu_transaction_test"))
    engine.dispose()


def test_postgres_borrowed_sessions_commit_together(postgres_engine: Any) -> None:
    manager = AtomicSessionManager(engine=postgres_engine, dialect="postgres")
    with manager.atomic():
        with manager.session() as first:
            first.execute(text("INSERT INTO memu_transaction_test VALUES (1, 'a')"))
            first.commit()
        with manager.session() as second:
            second.execute(text("INSERT INTO memu_transaction_test VALUES (2, 'b')"))
            second.commit()
    with postgres_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM memu_transaction_test")).scalar_one() == 2


def test_postgres_borrowed_session_failure_rolls_back(postgres_engine: Any) -> None:
    manager = AtomicSessionManager(engine=postgres_engine, dialect="postgres")
    with pytest.raises(ValueError, match="abort"), manager.atomic():
        with manager.session() as session:
            session.execute(text("INSERT INTO memu_transaction_test VALUES (1, 'a')"))
            session.commit()
        msg = "abort"
        raise ValueError(msg)
    with postgres_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM memu_transaction_test")).scalar_one() == 0


def test_postgres_serializes_independent_managers(postgres_engine: Any) -> None:
    first = AtomicSessionManager(engine=postgres_engine, dialect="postgres")
    second = AtomicSessionManager(engine=postgres_engine, dialect="postgres")
    holding = threading.Event()
    release = threading.Event()
    acquired = threading.Event()

    def hold() -> None:
        with first.atomic():
            holding.set()
            if not release.wait(timeout=5):
                raise TimeoutError

    def compete() -> None:
        with second.atomic():
            acquired.set()

    with ThreadPoolExecutor(max_workers=2) as executor:
        owner = executor.submit(hold)
        assert holding.wait(timeout=5)
        contender = executor.submit(compete)
        try:
            assert not acquired.wait(timeout=0.2)
        finally:
            release.set()
        owner.result(timeout=5)
        contender.result(timeout=5)
        assert acquired.is_set()


@pytest.fixture
def postgres_service(postgres_engine: Any, monkeypatch: Any) -> Any:
    from memu.database.postgres import postgres
    from memu.database.postgres.schema import get_sqlalchemy_models
    from tests.test_agentic import make_service

    def initialize(*, dsn: str, scope_model: Any, ddl_mode: str) -> None:
        del dsn, ddl_mode
        get_sqlalchemy_models(scope_model=scope_model).Base.metadata.create_all(postgres_engine)

    monkeypatch.setattr(postgres, "run_migrations", initialize)
    dsn = os.environ["MEMU_TEST_POSTGRES_DSN"]
    service = make_service({"metadata_store": {"provider": "postgres", "dsn": dsn}})
    yield service
    service.database.close()
    get_sqlalchemy_models(scope_model=service.user_model).Base.metadata.drop_all(postgres_engine)


async def test_postgres_public_concurrent_commit_keeps_index_consistent(postgres_service: Any) -> None:
    import asyncio

    from tests.test_commit_concurrency import PausedEmbeddings

    service = postgres_service
    embedder = PausedEmbeddings()
    service._embedding_pool._cache["embedding"] = embedder

    async def commit(value: str) -> None:
        await service.commit_results(
            recall_files=[{"name": "profile", "content": value}],
            resource=[{"path": "/note", "description": value}],
        )

    first = asyncio.create_task(commit("first"))
    second = asyncio.create_task(commit("second"))
    await asyncio.wait_for(embedder.both_waiting.wait(), timeout=2)
    embedder.release.set()
    await asyncio.gather(first, second)
    files = (await service.list_all_recall_files())["recall_files"]
    assert len(files) == 1
    segments = service.database.recall_file_segment_repo.list_segments_for_file(files[0]["id"])
    assert [segment.text for segment in segments] == [files[0]["content"]]
    assert len(service.database.resource_repo.list_resources()) == 1


async def test_postgres_public_commit_rolls_back_on_storage_failure(postgres_service: Any, monkeypatch: Any) -> None:
    service = postgres_service
    await service.commit_results(recall_files=[{"name": "profile", "content": "old"}])

    def fail(**kwargs: Any) -> None:
        msg = "injected failure"
        raise RuntimeError(msg)

    monkeypatch.setattr(service.database.recall_file_segment_repo, "create_segment", fail)
    with pytest.raises(RuntimeError, match="injected failure"):
        await service.commit_results(recall_files=[{"name": "profile", "content": "new"}])
    files = (await service.list_all_recall_files())["recall_files"]
    assert files[0]["content"] == "old"
    assert [segment.text for segment in service.database.recall_file_segment_repo.list_segments()] == ["old"]


def test_postgres_snapshot_keeps_one_version_while_writer_commits(postgres_engine: Any) -> None:
    reader = AtomicSessionManager(engine=postgres_engine, dialect="postgres")
    writer = AtomicSessionManager(engine=postgres_engine, dialect="postgres")
    with postgres_engine.begin() as connection:
        connection.execute(text("INSERT INTO memu_transaction_test VALUES (1, 'old')"))
    with reader.snapshot():
        with reader.session() as session:
            before = session.execute(text("SELECT value FROM memu_transaction_test WHERE id = 1")).scalar_one()
        with writer.atomic(), writer.session() as session:
            session.execute(text("UPDATE memu_transaction_test SET value = 'new' WHERE id = 1"))
            session.commit()
        with reader.session() as session:
            after = session.execute(text("SELECT value FROM memu_transaction_test WHERE id = 1")).scalar_one()
    assert before == after == "old"
    with postgres_engine.connect() as connection:
        assert connection.execute(text("SELECT value FROM memu_transaction_test WHERE id = 1")).scalar_one() == "new"


async def test_postgres_unscoped_commit_preserves_scoped_records(postgres_service: Any) -> None:
    service = postgres_service
    await service.commit_results(
        recall_files=[{"name": "profile", "content": "private"}],
        resource=[{"path": "/note", "description": "private"}],
        user={"user_id": "alice"},
    )
    await service.commit_results(
        recall_files=[{"name": "profile", "content": "public"}],
        resource=[{"path": "/note", "description": "public"}],
    )
    alice = {"user_id": "alice"}
    files = (await service.list_all_recall_files(where=alice))["recall_files"]
    assert [item["content"] for item in files] == ["private"]
    assert [item.caption for item in service.database.resource_repo.list_resources(alice).values()] == ["private"]
    all_files = (await service.list_all_recall_files())["recall_files"]
    assert sorted(item["content"] for item in all_files) == ["private", "public"]


@pytest.mark.parametrize("stage", ["resource", "file", "delete_segment", "create_segment"])
async def test_postgres_rolls_back_each_failed_write_stage(postgres_service: Any, monkeypatch: Any, stage: str) -> None:
    service = postgres_service
    await service.commit_results(
        recall_files=[{"name": "profile", "description": "before", "content": "old"}],
        resource=[{"path": "/note", "description": "before"}],
    )
    targets = {
        "resource": (service.database.resource_repo, "update_resource"),
        "file": (service.database.recall_file_repo, "update_recall_file"),
        "delete_segment": (service.database.recall_file_segment_repo, "delete_segment"),
        "create_segment": (service.database.recall_file_segment_repo, "create_segment"),
    }

    def fail(*args: Any, **kwargs: Any) -> None:
        msg = f"injected {stage} failure"
        raise RuntimeError(msg)

    target, method = targets[stage]
    with monkeypatch.context() as patch:
        patch.setattr(target, method, fail)
        with pytest.raises(RuntimeError, match=f"injected {stage} failure"):
            await service.commit_results(
                recall_files=[{"name": "profile", "description": "after", "content": "new"}],
                resource=[{"path": "/note", "description": "after"}],
            )
    assert (await service.list_all_recall_files())["recall_files"][0]["content"] == "old"
    assert [item.text for item in service.database.recall_file_segment_repo.list_segments()] == ["old"]
    assert [item.caption for item in service.database.resource_repo.list_resources().values()] == ["before"]
    await service.commit_results(recall_files=[{"name": "profile", "content": "recovered"}])


async def test_postgres_separate_services_replan_against_current_state(postgres_service: Any) -> None:
    import asyncio

    from tests.test_agentic import make_service
    from tests.test_commit_concurrency import PausedEmbeddings

    first = postgres_service
    second = make_service({"metadata_store": {"provider": "postgres", "dsn": os.environ["MEMU_TEST_POSTGRES_DSN"]}})
    embedder = PausedEmbeddings()
    first._embedding_pool._cache["embedding"] = embedder
    second._embedding_pool._cache["embedding"] = embedder
    try:
        tasks = [
            asyncio.create_task(service.commit_results(recall_files=[{"name": "profile", "content": content}]))
            for service, content in [(first, "first"), (second, "second")]
        ]
        await asyncio.wait_for(embedder.both_waiting.wait(), timeout=2)
        embedder.release.set()
        await asyncio.gather(*tasks)
        files = (await second.list_all_recall_files())["recall_files"]
        assert len(files) == 1
        segments = first.database.recall_file_segment_repo.list_segments_for_file(files[0]["id"])
        assert [item.text for item in segments] == [files[0]["content"]]
    finally:
        second.database.close()


def test_postgres_snapshot_exception_does_not_poison_later_transaction(postgres_engine: Any) -> None:
    manager = AtomicSessionManager(engine=postgres_engine, dialect="postgres")
    with pytest.raises(ValueError, match="reader failure"), manager.snapshot():
        with manager.session() as session:
            session.execute(text("SELECT count(*) FROM memu_transaction_test"))
        msg = "reader failure"
        raise ValueError(msg)
    with manager.atomic(), manager.session() as session:
        session.execute(text("INSERT INTO memu_transaction_test VALUES (1, 'ok')"))
        session.commit()
    with postgres_engine.connect() as connection:
        assert connection.execute(text("SELECT value FROM memu_transaction_test")).scalar_one() == "ok"
