"""Concurrent public commits must leave file content and its index consistent."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from tests.test_agentic import FakeEmbeddingClient, make_service


class PausedEmbeddings(FakeEmbeddingClient):
    def __init__(self) -> None:
        self.waiting = 0
        self.both_waiting = asyncio.Event()
        self.release = asyncio.Event()

    async def embed(self, inputs: list[str]) -> tuple[list[list[float]], None]:
        self.waiting += 1
        if self.waiting == 2:
            self.both_waiting.set()
        await self.release.wait()
        return await super().embed(inputs)


@pytest.mark.parametrize("provider", ["inmemory", "sqlite"])
async def test_overlapping_new_file_commits_leave_only_current_segments(provider: str, tmp_path: Any) -> None:
    config: dict[str, Any] = {"provider": provider}
    if provider == "sqlite":
        config["dsn"] = f"sqlite:///{tmp_path}/memu.sqlite3"
    service = make_service({"metadata_store": config})
    embedder = PausedEmbeddings()
    service._embedding_pool._cache["embedding"] = embedder

    async def commit(text: str) -> None:
        await service.commit_results(recall_files=[{"name": "profile", "content": text}])

    first = asyncio.create_task(commit("first value"))
    second = asyncio.create_task(commit("second value"))
    await asyncio.wait_for(embedder.both_waiting.wait(), timeout=2)
    embedder.release.set()
    await asyncio.gather(first, second)

    files = await service.list_all_recall_files()
    assert len(files["recall_files"]) == 1
    content = files["recall_files"][0]["content"]
    segments = service.database.recall_file_segment_repo.list_segments_for_file(files["recall_files"][0]["id"])
    assert [segment.text for segment in segments] == [content]


@pytest.mark.parametrize("provider", ["inmemory", "sqlite"])
async def test_overlapping_resource_commits_do_not_duplicate_path(provider: str, tmp_path: Any) -> None:
    config: dict[str, Any] = {"provider": provider}
    if provider == "sqlite":
        config["dsn"] = f"sqlite:///{tmp_path}/memu.sqlite3"
    service = make_service({"metadata_store": config})
    embedder = PausedEmbeddings()
    service._embedding_pool._cache["embedding"] = embedder

    async def commit(description: str) -> None:
        await service.commit_results(resource=[{"path": "/note", "description": description}])

    first = asyncio.create_task(commit("first"))
    second = asyncio.create_task(commit("second"))
    await asyncio.wait_for(embedder.both_waiting.wait(), timeout=2)
    embedder.release.set()
    await asyncio.gather(first, second)

    resources = service.database.resource_repo.list_resources()
    assert len(resources) == 1


@pytest.mark.parametrize("provider", ["inmemory", "sqlite"])
async def test_write_failure_rolls_back_the_entire_commit(provider: str, tmp_path: Any, monkeypatch: Any) -> None:
    config: dict[str, Any] = {"provider": provider}
    if provider == "sqlite":
        config["dsn"] = f"sqlite:///{tmp_path}/memu.sqlite3"
    service = make_service({"metadata_store": config})
    await service.commit_results(
        recall_files=[{"name": "profile", "content": "original"}],
        resource=[{"path": "/note", "description": "original"}],
    )

    def fail_create(**kwargs: Any) -> None:
        msg = "injected storage failure"
        raise RuntimeError(msg)

    monkeypatch.setattr(service.database.recall_file_segment_repo, "create_segment", fail_create)
    with pytest.raises(RuntimeError, match="injected storage failure"):
        await service.commit_results(
            recall_files=[{"name": "profile", "content": "new"}],
            resource=[{"path": "/note", "description": "new"}],
        )
    files = await service.list_all_recall_files()
    assert files["recall_files"][0]["content"] == "original"
    assert [segment.text for segment in service.database.recall_file_segment_repo.list_segments()] == ["original"]
    assert [resource.caption for resource in service.database.resource_repo.list_resources().values()] == ["original"]


async def test_separate_sqlite_services_replan_after_other_commit(tmp_path: Any) -> None:
    config = {"metadata_store": {"provider": "sqlite", "dsn": f"sqlite:///{tmp_path}/memu.sqlite3"}}
    first_service = make_service(config)
    second_service = make_service(config)
    embedder = PausedEmbeddings()
    first_service._embedding_pool._cache["embedding"] = embedder
    second_service._embedding_pool._cache["embedding"] = embedder

    first = asyncio.create_task(first_service.commit_results(recall_files=[{"name": "one", "content": "old"}]))
    second = asyncio.create_task(second_service.commit_results(recall_files=[{"name": "one", "content": "new"}]))
    await asyncio.wait_for(embedder.both_waiting.wait(), timeout=2)
    embedder.release.set()
    await asyncio.gather(first, second)
    files = (await second_service.list_all_recall_files())["recall_files"]
    assert len(files) == 1
    segments = first_service.database.recall_file_segment_repo.list_segments_for_file(files[0]["id"])
    assert [segment.text for segment in segments] == [files[0]["content"]]


@pytest.mark.parametrize("provider", ["inmemory", "sqlite"])
async def test_commit_scope_does_not_remove_another_users_segments(provider: str, tmp_path: Any) -> None:
    config: dict[str, Any] = {"provider": provider}
    if provider == "sqlite":
        config["dsn"] = f"sqlite:///{tmp_path}/memu.sqlite3"
    service = make_service({"metadata_store": config})
    for user, content in [("alice", "alice original"), ("bob", "bob original")]:
        await service.commit_results(recall_files=[{"name": "profile", "content": content}], user={"user_id": user})
    await service.commit_results(recall_files=[{"name": "profile", "content": "alice new"}], user={"user_id": "alice"})
    files = (await service.list_all_recall_files(where={"user_id": "bob"}))["recall_files"]
    assert [item["content"] for item in files] == ["bob original"]
    segments = service.database.recall_file_segment_repo.list_segments_for_file(files[0]["id"])
    assert [item.text for item in segments] == ["bob original"]


@pytest.mark.parametrize("provider", ["inmemory", "sqlite"])
async def test_cancelled_embedding_leaves_previous_data_intact(provider: str, tmp_path: Any) -> None:
    config: dict[str, Any] = {"provider": provider}
    if provider == "sqlite":
        config["dsn"] = f"sqlite:///{tmp_path}/memu.sqlite3"
    service = make_service({"metadata_store": config})
    await service.commit_results(recall_files=[{"name": "profile", "content": "original"}])
    embedder = PausedEmbeddings()
    service._embedding_pool._cache["embedding"] = embedder
    task = asyncio.create_task(service.commit_results(recall_files=[{"name": "profile", "content": "new"}]))
    while not embedder.waiting:
        await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    files = (await service.list_all_recall_files())["recall_files"]
    assert files[0]["content"] == "original"
    assert [item.text for item in service.database.recall_file_segment_repo.list_segments()] == ["original"]
    service._embedding_pool._cache["embedding"] = FakeEmbeddingClient()
    await service.commit_results(recall_files=[{"name": "profile", "content": "next"}])
    assert (await service.list_all_recall_files())["recall_files"][0]["content"] == "next"


def _commit_in_process(dsn: str, value: str, ready: Any, release: Any, outcomes: Any) -> None:
    class ProcessEmbedding(FakeEmbeddingClient):
        async def embed(self, inputs: list[str]) -> tuple[list[list[float]], None]:
            ready.put(value)
            if not release.wait(timeout=10):
                msg = "parent did not release embedding barrier"
                raise TimeoutError(msg)
            return await super().embed(inputs)

    async def run() -> None:
        service = make_service({"metadata_store": {"provider": "sqlite", "dsn": dsn}})
        service._embedding_pool._cache["embedding"] = ProcessEmbedding()
        await service.commit_results(
            recall_files=[{"name": "profile", "content": value}],
            resource=[{"path": "/note", "description": value}],
        )
        service.database.close()

    try:
        asyncio.run(run())
        outcomes.put((value, "ok"))
    except BaseException as exc:
        outcomes.put((value, repr(exc)))
        raise


def test_sqlite_commit_serializes_independent_processes(tmp_path: Any) -> None:
    import multiprocessing

    dsn = f"sqlite:///{tmp_path}/memu.sqlite3"
    service = make_service({"metadata_store": {"provider": "sqlite", "dsn": dsn}})
    context = multiprocessing.get_context("spawn")
    ready = context.Queue()
    outcomes = context.Queue()
    release = context.Event()
    processes = [
        context.Process(target=_commit_in_process, args=(dsn, value, ready, release, outcomes))
        for value in ("first", "second")
    ]
    try:
        for process in processes:
            process.start()
        assert {ready.get(timeout=15), ready.get(timeout=15)} == {"first", "second"}
        release.set()
        results = [outcomes.get(timeout=15), outcomes.get(timeout=15)]
        for process in processes:
            process.join(timeout=15)
            assert process.exitcode == 0
        assert sorted(status for _, status in results) == ["ok", "ok"]
        files = asyncio.run(service.list_all_recall_files())["recall_files"]
        assert len(files) == 1
        assert [segment.text for segment in service.database.recall_file_segment_repo.list_segments()] == [
            files[0]["content"]
        ]
        assert len(service.database.resource_repo.list_resources()) == 1
    finally:
        release.set()
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
        service.database.close()
        ready.close()
        outcomes.close()


@pytest.mark.parametrize("provider", ["inmemory", "sqlite"])
def test_retrieval_does_not_observe_partial_commit(provider: str, tmp_path: Any, monkeypatch: Any) -> None:
    import threading
    from concurrent.futures import ThreadPoolExecutor

    config: dict[str, Any] = {"provider": provider}
    if provider == "sqlite":
        config["dsn"] = f"sqlite:///{tmp_path}/memu.sqlite3"
    service = make_service({"metadata_store": config})
    asyncio.run(service.commit_results(recall_files=[{"name": "profile", "content": "coffee old"}]))
    entered = threading.Event()
    release = threading.Event()
    original = service.database.recall_file_segment_repo.create_segment

    def pause_create(**kwargs: Any) -> Any:
        entered.set()
        if not release.wait(timeout=5):
            raise TimeoutError
        return original(**kwargs)

    monkeypatch.setattr(service.database.recall_file_segment_repo, "create_segment", pause_create)
    with ThreadPoolExecutor(max_workers=2) as executor:
        writer = executor.submit(
            lambda: asyncio.run(service.commit_results(recall_files=[{"name": "profile", "content": "coffee new"}]))
        )
        assert entered.wait(timeout=5)
        reader = executor.submit(lambda: asyncio.run(service.progressive_retrieve("coffee")))
        try:
            # Give a broken reader a chance to observe the paused write; a correct
            # reader may wait for publication or return the previous snapshot.
            try:
                result = reader.result(timeout=0.2)
            except TimeoutError:
                result = None
        finally:
            release.set()
        writer.result(timeout=5)
        if result is None:
            result = reader.result(timeout=5)
        assert [segment["text"] for segment in result["segments"]] in [["coffee old"], ["coffee new"]]


@pytest.mark.parametrize("provider", ["inmemory", "sqlite"])
async def test_replan_embeds_newly_required_vectors(provider: str, tmp_path: Any) -> None:
    config: dict[str, Any] = {"provider": provider}
    if provider == "sqlite":
        config["dsn"] = f"sqlite:///{tmp_path}/memu.sqlite3"
    service = make_service({"metadata_store": config})
    await service.commit_results(recall_files=[{"name": "profile", "description": "old", "content": "seed"}])
    embedder = PausedEmbeddings()
    service._embedding_pool._cache["embedding"] = embedder
    first = asyncio.create_task(
        service.commit_results(recall_files=[{"name": "profile", "description": "new", "content": "one"}])
    )
    second = asyncio.create_task(
        service.commit_results(recall_files=[{"name": "profile", "description": "old", "content": "two"}])
    )
    await asyncio.wait_for(embedder.both_waiting.wait(), timeout=2)
    embedder.release.set()
    await asyncio.gather(first, second)
    files = (await service.list_all_recall_files())["recall_files"]
    assert files[0]["description"] == "old"
    assert files[0]["content"] == "two"
    assert embedder.waiting == 3
    stored = next(iter(service.database.recall_file_repo.list_recall_files().values()))
    expected, _ = await FakeEmbeddingClient().embed(["profile: old"])
    assert stored.embedding == expected[0]


@pytest.mark.parametrize("provider", ["inmemory", "sqlite"])
@pytest.mark.parametrize("stage", ["resource", "file", "delete_segment", "create_segment"])
async def test_failures_at_each_write_stage_restore_all_records(
    provider: str, stage: str, tmp_path: Any, monkeypatch: Any
) -> None:
    config: dict[str, Any] = {"provider": provider}
    if provider == "sqlite":
        config["dsn"] = f"sqlite:///{tmp_path}/memu.sqlite3"
    service = make_service({"metadata_store": config})
    await service.commit_results(
        recall_files=[{"name": "profile", "description": "before", "content": "old line"}],
        resource=[{"path": "/note", "description": "before"}],
    )
    targets = {
        "resource": (service.database.resource_repo, "update_resource"),
        "file": (service.database.recall_file_repo, "update_recall_file"),
        "delete_segment": (service.database.recall_file_segment_repo, "delete_segment"),
        "create_segment": (service.database.recall_file_segment_repo, "create_segment"),
    }

    def fail(*args: Any, **kwargs: Any) -> None:
        msg = f"failure at {stage}"
        raise RuntimeError(msg)

    with monkeypatch.context() as patch:
        target, method = targets[stage]
        patch.setattr(target, method, fail)
        with pytest.raises(RuntimeError, match=f"failure at {stage}"):
            await service.commit_results(
                recall_files=[{"name": "profile", "description": "after", "content": "new line"}],
                resource=[{"path": "/note", "description": "after"}],
            )
    files = (await service.list_all_recall_files())["recall_files"]
    assert [(item["description"], item["content"]) for item in files] == [("before", "old line")]
    assert [item.text for item in service.database.recall_file_segment_repo.list_segments()] == ["old line"]
    assert [item.caption for item in service.database.resource_repo.list_resources().values()] == ["before"]
    # An exception must release the lock and leave the store usable.
    await service.commit_results(recall_files=[{"name": "profile", "content": "recovered"}])
    assert (await service.list_all_recall_files())["recall_files"][0]["content"] == "recovered"


@pytest.mark.parametrize("provider", ["inmemory", "sqlite"])
async def test_conflict_reembedding_failure_does_not_overwrite_winner(provider: str, tmp_path: Any) -> None:
    config: dict[str, Any] = {"provider": provider}
    if provider == "sqlite":
        config["dsn"] = f"sqlite:///{tmp_path}/memu.sqlite3"
    service = make_service({"metadata_store": config})
    await service.commit_results(recall_files=[{"name": "profile", "description": "old", "content": "seed"}])
    entered = asyncio.Event()
    release = asyncio.Event()

    class FailsOnRetry(FakeEmbeddingClient):
        def __init__(self) -> None:
            self.calls = 0

        async def embed(self, inputs: list[str]) -> tuple[list[list[float]], None]:
            self.calls += 1
            if self.calls > 1:
                msg = "embedding unavailable on retry"
                raise RuntimeError(msg)
            entered.set()
            await release.wait()
            return await super().embed(inputs)

    embedder = FailsOnRetry()
    service._embedding_pool._cache["embedding"] = embedder
    pending = asyncio.create_task(
        service.commit_results(recall_files=[{"name": "profile", "description": "old", "content": "loser"}])
    )
    await asyncio.wait_for(entered.wait(), timeout=2)
    service._embedding_pool._cache["embedding"] = FakeEmbeddingClient()
    await service.commit_results(recall_files=[{"name": "profile", "description": "new", "content": "winner"}])
    release.set()
    with pytest.raises(RuntimeError, match="embedding unavailable on retry"):
        await pending
    files = (await service.list_all_recall_files())["recall_files"]
    assert [(item["description"], item["content"]) for item in files] == [("new", "winner")]
    assert [item.text for item in service.database.recall_file_segment_repo.list_segments()] == ["winner"]


@pytest.mark.parametrize("provider", ["inmemory", "sqlite"])
async def test_snapshot_failure_releases_locks_and_keeps_the_store_usable(provider: str, tmp_path: Any) -> None:
    config: dict[str, Any] = {"provider": provider}
    if provider == "sqlite":
        config["dsn"] = f"sqlite:///{tmp_path}/memu.sqlite3"
    service = make_service({"metadata_store": config})
    await service.commit_results(recall_files=[{"name": "profile", "content": "old"}])
    with pytest.raises(ValueError, match="reader failed"), service.database.snapshot():
        assert service.database.recall_file_repo.list_recall_files()
        msg = "reader failed"
        raise ValueError(msg)
    await service.commit_results(recall_files=[{"name": "profile", "content": "new"}])
    assert (await service.list_all_recall_files())["recall_files"][0]["content"] == "new"


@pytest.mark.parametrize("provider", ["inmemory", "sqlite"])
async def test_unchanged_commit_does_not_call_embedding_provider(provider: str, tmp_path: Any) -> None:
    config: dict[str, Any] = {"provider": provider}
    if provider == "sqlite":
        config["dsn"] = f"sqlite:///{tmp_path}/memu.sqlite3"
    service = make_service({"metadata_store": config})
    payload = [{"name": "profile", "description": "person", "content": "coffee"}]
    await service.commit_results(recall_files=payload)

    class UnavailableEmbedding(FakeEmbeddingClient):
        async def embed(self, inputs: list[str]) -> tuple[list[list[float]], None]:
            msg = "unchanged commits should not embed"
            raise AssertionError(msg)

    service._embedding_pool._cache["embedding"] = UnavailableEmbedding()
    await service.commit_results(recall_files=payload)
    files = (await service.list_all_recall_files())["recall_files"]
    assert [(item["description"], item["content"]) for item in files] == [("person", "coffee")]
    assert [item.text for item in service.database.recall_file_segment_repo.list_segments()] == ["coffee"]


def test_sqlite_snapshot_survives_another_services_commit(tmp_path: Any) -> None:
    from concurrent.futures import ThreadPoolExecutor

    from sqlalchemy import text

    config = {"metadata_store": {"provider": "sqlite", "dsn": f"sqlite:///{tmp_path}/memu.sqlite3"}}
    reader = make_service(config)
    writer = make_service(config)
    # WAL permits the writer to publish while the reader holds its older snapshot.
    with reader.database._sessions.engine.connect() as connection:
        connection.execute(text("PRAGMA journal_mode=WAL"))
    asyncio.run(writer.commit_results(recall_files=[{"name": "profile", "content": "old"}]))
    try:
        with ThreadPoolExecutor(max_workers=1) as executor, reader.database.snapshot():
            assert [item.text for item in reader.database.recall_file_segment_repo.list_segments()] == ["old"]
            future = executor.submit(
                lambda: asyncio.run(writer.commit_results(recall_files=[{"name": "profile", "content": "new"}]))
            )
            future.result(timeout=5)
            files = reader.database.recall_file_repo.list_recall_files().values()
            assert [item.content for item in files] == ["old"]
        assert [item.content for item in reader.database.recall_file_repo.list_recall_files().values()] == ["new"]
    finally:
        reader.database.close()
        writer.database.close()


async def test_database_without_atomic_capability_keeps_working(monkeypatch: Any) -> None:
    from types import SimpleNamespace

    from memu.database.interfaces import AtomicDatabase, Database

    service = make_service({"metadata_store": {"provider": "inmemory"}})
    store = service.database
    legacy = SimpleNamespace(
        resource_repo=store.resource_repo,
        recall_file_repo=store.recall_file_repo,
        recall_file_segment_repo=store.recall_file_segment_repo,
        resources=store.resources,
        recall_files=store.recall_files,
        segments=store.segments,
        close=store.close,
    )
    assert isinstance(legacy, Database)
    assert not isinstance(legacy, AtomicDatabase)
    monkeypatch.setattr(service, "_get_database", lambda: legacy)
    await service.commit_results(recall_files=[{"name": "profile", "content": "coffee"}])
    assert (await service.list_all_recall_files())["recall_files"][0]["content"] == "coffee"
    assert (await service.progressive_retrieve("coffee"))["segments"][0]["text"] == "coffee"


@pytest.mark.parametrize("provider", ["inmemory", "sqlite"])
async def test_late_failure_rolls_back_new_and_updated_files(provider: str, tmp_path: Any, monkeypatch: Any) -> None:
    config: dict[str, Any] = {"provider": provider}
    if provider == "sqlite":
        config["dsn"] = f"sqlite:///{tmp_path}/memu.sqlite3"
    service = make_service({"metadata_store": config})
    await service.commit_results(recall_files=[{"name": "profile", "content": "old"}])
    original = service.database.recall_file_segment_repo.create_segment

    def fail_after_insert(**kwargs: Any) -> Any:
        segment = original(**kwargs)
        if kwargs["text"] == "last":
            msg = "failure after last insert"
            raise RuntimeError(msg)
        return segment

    with monkeypatch.context() as patch:
        patch.setattr(service.database.recall_file_segment_repo, "create_segment", fail_after_insert)
        with pytest.raises(RuntimeError, match="failure after last insert"):
            await service.commit_results(
                recall_files=[{"name": "profile", "content": "new"}, {"name": "added", "content": "last"}]
            )
    files = (await service.list_all_recall_files())["recall_files"]
    assert [(item["name"], item["content"]) for item in files] == [("profile", "old")]
    assert [item.text for item in service.database.recall_file_segment_repo.list_segments()] == ["old"]
