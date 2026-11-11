"""Cross-thread public commit isolation at planning and response boundaries."""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from typing import Any

import pytest
from pydantic import BaseModel

from memu.database.inmemory.repositories import recall_file_repo
from tests.test_agentic import make_service


def test_initial_commit_plan_is_a_consistent_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    service = make_service({"metadata_store": {"provider": "inmemory"}})
    asyncio.run(service.commit_results(recall_files=[{"name": "profile", "content": "seed"}]))
    entered, release = threading.Event(), threading.Event()
    original = recall_file_repo.matches_where
    paused_thread: int | None = None
    did_pause = False

    def pause_match(obj: Any, where: Any) -> bool:
        nonlocal did_pause
        if threading.get_ident() == paused_thread and not did_pause:
            did_pause = True
            entered.set()
            assert release.wait(5)
        return original(obj, where)

    monkeypatch.setattr(recall_file_repo, "matches_where", pause_match)

    def plan() -> dict[str, Any]:
        nonlocal paused_thread
        paused_thread = threading.get_ident()
        return asyncio.run(service.commit_results(recall_files=[{"name": "profile", "content": "updated"}]))

    def add_file() -> dict[str, Any]:
        return asyncio.run(service.commit_results(recall_files=[{"name": "second", "content": "other"}]))

    with ThreadPoolExecutor(max_workers=2) as executor:
        planner = executor.submit(plan)
        assert entered.wait(5)
        writer = executor.submit(add_file)
        try:
            with suppress(TimeoutError):
                writer.result(timeout=0.2)
        finally:
            release.set()
        planner.result(timeout=5)
        writer.result(timeout=5)
    files = asyncio.run(service.list_all_recall_files())["recall_files"]
    assert {item["name"]: item["content"] for item in files} == {"profile": "updated", "second": "other"}


def test_commit_response_belongs_to_its_transaction(monkeypatch: pytest.MonkeyPatch) -> None:
    service = make_service({"metadata_store": {"provider": "inmemory"}})
    asyncio.run(service.commit_results(recall_files=[{"name": "profile", "content": "seed"}]))
    entered, release = threading.Event(), threading.Event()
    original = service._model_dump_without_embeddings
    paused_thread: int | None = None
    did_pause = False

    def pause_dump(obj: BaseModel) -> dict[str, Any]:
        nonlocal did_pause
        if threading.get_ident() == paused_thread and not did_pause:
            did_pause = True
            entered.set()
            assert release.wait(5)
        return original(obj)

    monkeypatch.setattr(service, "_model_dump_without_embeddings", pause_dump)

    def first_commit() -> dict[str, Any]:
        nonlocal paused_thread
        paused_thread = threading.get_ident()
        return asyncio.run(service.commit_results(recall_files=[{"name": "profile", "content": "first"}]))

    def second_commit() -> dict[str, Any]:
        return asyncio.run(service.commit_results(recall_files=[{"name": "profile", "content": "second"}]))

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(first_commit)
        assert entered.wait(5)
        second = executor.submit(second_commit)
        try:
            with suppress(TimeoutError):
                second.result(timeout=0.2)
        finally:
            release.set()
        first_result, second_result = first.result(timeout=5), second.result(timeout=5)
    assert first_result["recall_files"][0]["content"] == "first"
    assert second_result["recall_files"][0]["content"] == "second"
