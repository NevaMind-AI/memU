from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from memu.app.memorize import lifecycle as lifecycle_module
from memu.app.memorize.input import MemorizeInput, MessageInput
from memu.app.memorize.lifecycle import MemorizeWorkspace, commit_memorize, prepare_memorize


class FakeBackend:
    def __init__(self, pages: list[list[dict[str, Any]]] | None = None) -> None:
        self.pages = pages or [[]]
        self.list_cursors: list[str | None] = []
        self.commits: list[dict[str, Any]] = []
        self.fail_list = False
        self.fail_commit = False

    async def list_all_recall_files(
        self,
        where: dict[str, Any] | None = None,
        *,
        cursor: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        del where, limit
        if self.fail_list:
            msg = "list failed"
            raise RuntimeError(msg)
        self.list_cursors.append(cursor)
        index = 0 if cursor is None else int(cursor)
        next_cursor = str(index + 1) if index + 1 < len(self.pages) else None
        return {"recall_files": self.pages[index], "next_cursor": next_cursor}

    async def progressive_retrieve(
        self,
        query: str,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        del query, where
        return {}

    async def commit_results(
        self,
        *,
        recall_files: list[dict[str, Any]] | None = None,
        resource: list[dict[str, Any]] | None = None,
        user: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        del user
        if self.fail_commit:
            msg = "commit failed"
            raise RuntimeError(msg)
        payload = {"recall_files": recall_files or [], "resource": resource or []}
        self.commits.append(payload)
        return {"recall_files": payload["recall_files"], "resources": payload["resource"]}


def _input(content: str = "Hello") -> MemorizeInput:
    return MemorizeInput(items=[MessageInput(role="user", content=content)])


@pytest.fixture(autouse=True)
def embedded_templates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lifecycle_module.templates, "resolve", lambda _name, embedded: embedded)


async def test_prepare_mirrors_all_pages_and_returns_ordered_jobs(tmp_path: Path) -> None:
    backend = FakeBackend([
        [{"name": "profile", "track": "memory", "description": "user profile", "content": "likes tea"}],
        [
            {"name": "deploy", "track": "skill", "description": "deploy workflow", "content": "ship it"},
            {"name": "ignored", "track": "other", "description": "ignored", "content": "ignored"},
        ],
    ])
    workspace = MemorizeWorkspace(tmp_path / "workspace")

    prepared = await prepare_memorize(_input(), workspace, backend, verify_command="memu verify")

    assert backend.list_cursors == [None, "1"]
    assert [path.name for path in prepared.jobs] == ["1.txt", "2.txt", "3.txt"]
    assert (workspace.memory / "profile.md").exists()
    assert (workspace.skill / "deploy.md").exists()
    assert not (workspace.base / "other" / "ignored.md").exists()
    assert str(prepared.transcript.memory_path) in prepared.jobs[0].read_text(encoding="utf-8")
    assert str(prepared.transcript.skill_path) in prepared.jobs[1].read_text(encoding="utf-8")
    assert "memu verify" in prepared.jobs[-1].read_text(encoding="utf-8")
    assert workspace.active_run.read_text(encoding="utf-8") == '{"schema_version":"1.0"}\n'


async def test_prepare_batch_materializes_sessions_and_orders_jobs(tmp_path: Path) -> None:
    workspace = MemorizeWorkspace(tmp_path / "workspace")

    prepared = await prepare_memorize([_input("First"), _input("Second")], workspace, FakeBackend(), verify_command="memu verify")

    assert [path.name for path in prepared.jobs] == ["1.txt", "2.txt", "3.txt", "4.txt", "5.txt"]
    assert (workspace.input / "1.jsonl").is_file()
    assert (workspace.input / "2.jsonl").is_file()
    assert (workspace.input / "1_full.jsonl").is_file()
    assert (workspace.input / "2_full.jsonl").is_file()
    assert str(workspace.input / "1.jsonl") in prepared.jobs[0].read_text(encoding="utf-8")
    assert str(workspace.input / "2.jsonl") in prepared.jobs[1].read_text(encoding="utf-8")
    assert str(workspace.input / "1_full.jsonl") in prepared.jobs[2].read_text(encoding="utf-8")
    assert str(workspace.input / "2_full.jsonl") in prepared.jobs[3].read_text(encoding="utf-8")
    assert "memu verify" in prepared.jobs[4].read_text(encoding="utf-8")


async def test_commit_submits_only_changed_recall_files_and_resources(tmp_path: Path) -> None:
    backend = FakeBackend([
        [{"name": "profile", "track": "memory", "description": "user profile", "content": "likes tea"}],
    ])
    workspace = MemorizeWorkspace(tmp_path / "workspace")
    await prepare_memorize(_input(), workspace, backend, verify_command="memu verify")
    (workspace.memory / "profile.md").write_text(
        "---\nname: profile\ndescription: user profile\n---\nlikes dark roast",
        encoding="utf-8",
    )
    workspace.skill.mkdir(parents=True, exist_ok=True)
    (workspace.skill / "brew.md").write_text(
        "---\nname: brew\ndescription: brew coffee\n---\ngrind then pour",
        encoding="utf-8",
    )
    workspace.resources.write_text(
        "---\npath: /workspace/coffee.md\ndescription: coffee notes\n---\n",
        encoding="utf-8",
    )

    result = await commit_memorize(workspace, backend)

    committed = backend.commits[0]
    assert [(item["track"], item["name"]) for item in committed["recall_files"]] == [
        ("memory", "profile"),
        ("skill", "brew"),
    ]
    assert committed["resource"] == [{"path": "/workspace/coffee.md", "description": "coffee notes"}]
    assert len(result["recall_files"]) == 2
    assert not workspace.active_run.exists()
    assert list(workspace.jobs.glob("*.txt")) == []
    assert list(workspace.input.glob("*.jsonl")) == []
    assert not workspace.resources.exists()


async def test_prepare_rejects_second_session_without_touching_active_run(tmp_path: Path) -> None:
    backend = FakeBackend()
    workspace = MemorizeWorkspace(tmp_path / "workspace")
    prepared = await prepare_memorize(_input(), workspace, backend, verify_command="memu verify")
    marker = workspace.active_run.read_bytes()
    transcript = prepared.transcript.memory_path.read_bytes()

    with pytest.raises(RuntimeError, match="already has an active run"):
        await prepare_memorize(_input("Second"), workspace, backend, verify_command="memu verify")

    assert workspace.active_run.read_bytes() == marker
    assert prepared.transcript.memory_path.read_bytes() == transcript
    assert backend.list_cursors == [None]


async def test_prepare_failure_does_not_open_a_run(tmp_path: Path) -> None:
    backend = FakeBackend()
    backend.fail_list = True
    workspace = MemorizeWorkspace(tmp_path / "workspace")

    with pytest.raises(RuntimeError, match="list failed"):
        await prepare_memorize(_input(), workspace, backend, verify_command="memu verify")

    assert not workspace.active_run.exists()


async def test_failed_commit_preserves_run_for_retry(tmp_path: Path) -> None:
    backend = FakeBackend()
    workspace = MemorizeWorkspace(tmp_path / "workspace")
    await prepare_memorize(_input(), workspace, backend, verify_command="memu verify")
    workspace.memory.mkdir(parents=True, exist_ok=True)
    (workspace.memory / "note.md").write_text("---\nname: note\n---\nremember me", encoding="utf-8")
    backend.fail_commit = True

    with pytest.raises(RuntimeError, match="commit failed"):
        await commit_memorize(workspace, backend)

    assert workspace.active_run.exists()
    assert list(workspace.jobs.glob("*.txt"))
    assert list(workspace.input.glob("*.jsonl"))
    assert (workspace.memory / "note.md").exists()

    backend.fail_commit = False
    await commit_memorize(workspace, backend)
    assert [item["name"] for item in backend.commits[0]["recall_files"]] == ["note"]
    assert not workspace.active_run.exists()


async def test_noop_commit_allows_next_session(tmp_path: Path) -> None:
    backend = FakeBackend()
    workspace = MemorizeWorkspace(tmp_path / "workspace")
    await prepare_memorize(_input(), workspace, backend, verify_command="memu verify")

    result = await commit_memorize(workspace, backend)
    next_run = await prepare_memorize(_input("Second"), workspace, backend, verify_command="memu verify")

    assert result == {"recall_files": [], "resources": []}
    assert backend.commits[0] == {"recall_files": [], "resource": []}
    assert next_run.transcript.memory_path.is_file()


async def test_commit_requires_active_run(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="no active run"):
        await commit_memorize(MemorizeWorkspace(tmp_path / "workspace"), FakeBackend())
