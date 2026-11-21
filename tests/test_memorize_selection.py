from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from memu import cli
from memu.app import MemoryService
from memu.app.memorize import lifecycle
from memu.app.memorize.input import MemorizeInput, MessageInput
from memu.app.memorize.lifecycle import MemorizeWorkspace, commit_memorize, prepare_memorize
from memu.hosts import templates


@pytest.fixture()
def backend() -> Any:
    return SimpleNamespace(
        list_all_recall_files=AsyncMock(return_value={"recall_files": [], "next_cursor": None}),
        commit_results=AsyncMock(return_value={"recall_files": [], "resources": []}),
    )


def _session() -> MemorizeInput:
    return MemorizeInput(items=[MessageInput(role="user", content="Use concise explanations.")])


def _write_memory(workspace: MemorizeWorkspace, name: str = "note") -> Path:
    workspace.memory.mkdir(parents=True, exist_ok=True)
    path = workspace.memory / f"{name}.md"
    path.write_text(f"---\nname: {name}\n---\nUse concise explanations.\n", encoding="utf-8")
    return path


def _files(base: Path) -> dict[str, bytes]:
    return {path.relative_to(base).as_posix(): path.read_bytes() for path in base.rglob("*") if path.is_file()}


@pytest.mark.parametrize("count", [1, 10])
async def test_memory_only_prepares_selected_jobs_and_mirrors_all_pages(
    tmp_path: Path, backend: Any, monkeypatch: pytest.MonkeyPatch, count: int
) -> None:
    workspace = MemorizeWorkspace(tmp_path / "workspace")
    backend.list_all_recall_files.side_effect = [
        {
            "recall_files": [
                {"track": "skill", "name": "deploy", "content": "deploy steps"},
                {"track": "memory", "name": "profile", "content": "concise explanations"},
            ],
            "next_cursor": "next-page",
        },
        {"recall_files": [{"track": "memory", "name": "editor", "content": "editor preference"}], "next_cursor": None},
    ]
    resolved: list[str] = []

    def resolve(name: str, embedded: str) -> str:
        resolved.append(name)
        return embedded

    monkeypatch.setattr(templates, "resolve", resolve)
    prepared = await prepare_memorize(
        [_session() for _ in range(count)], workspace, backend, verify_command="offline-verify", only="memory"
    )

    assert [path.name for path in prepared.jobs] == [f"{index}.txt" for index in range(1, count + 1)]
    for transcript, job in zip(prepared.transcripts, prepared.jobs, strict=True):
        assert transcript.memory_path.is_file()
        assert transcript.skill_path.is_file()
        assert str(transcript.memory_path) in job.read_text(encoding="utf-8")
        assert "offline-verify" not in job.read_text(encoding="utf-8")
    assert resolved == [templates.MEMORY_JOB]
    assert backend.list_all_recall_files.await_args_list[0].kwargs == {"cursor": None}
    assert backend.list_all_recall_files.await_args_list[1].kwargs == {"cursor": "next-page"}
    assert not workspace.skill.exists()
    assert sorted(json.loads(workspace.manifest.read_text(encoding="utf-8"))) == [
        "memory/editor.md",
        "memory/profile.md",
    ]
    assert json.loads(workspace.active_run.read_text(encoding="utf-8"))["evolve_selection"] == "memory"


async def test_memory_only_ignores_unselected_files_without_parsing(
    tmp_path: Path, backend: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = MemorizeWorkspace(tmp_path / "workspace")
    workspace.skill.mkdir(parents=True)
    skill = workspace.skill / "caller-owned.md"
    skill.write_bytes(b"\xff\xfe")
    workspace.resources.write_bytes(b"\xff\xfe")
    workspace.resource_log.write_bytes(b"\xff")
    await prepare_memorize(_session(), workspace, backend, verify_command="offline-verify", only="memory")
    assert workspace.resources.read_bytes() == b"\xff\xfe"
    assert workspace.resource_log.read_bytes() == b"\xff"
    _write_memory(workspace)

    def unexpected_resource_parse(_path: Path) -> Any:
        pytest.fail("memory-only must not parse the resource file")

    monkeypatch.setattr(lifecycle, "read_resources", unexpected_resource_parse)
    await commit_memorize(workspace, backend)

    submitted = backend.commit_results.await_args.kwargs
    assert [(item["track"], item["name"]) for item in submitted["recall_files"]] == [("memory", "note")]
    assert submitted["resource"] == []
    assert workspace.base.is_dir()
    assert skill.read_bytes() == b"\xff\xfe"
    assert workspace.resources.read_bytes() == b"\xff\xfe"
    assert workspace.resource_log.read_bytes() == b"\xff"
    assert list(json.loads(workspace.manifest.read_text(encoding="utf-8"))) == ["memory/note.md"]


async def test_legacy_marker_keeps_full_commit_behavior(tmp_path: Path, backend: Any) -> None:
    workspace = MemorizeWorkspace(tmp_path / "workspace")
    await prepare_memorize(_session(), workspace, backend, verify_command="offline-verify")
    marker = json.loads(workspace.active_run.read_text(encoding="utf-8"))
    assert marker.pop("evolve_selection") == "all"
    workspace.active_run.write_text(json.dumps(marker), encoding="utf-8")
    _write_memory(workspace)
    workspace.skill.mkdir()
    (workspace.skill / "deploy.md").write_text("---\nname: deploy\n---\nRun the tests.\n", encoding="utf-8")
    workspace.resources.write_text(
        "---\npath: /synthetic/notes.md\ndescription: project notes\n---\n", encoding="utf-8"
    )

    await commit_memorize(workspace, backend)

    submitted = backend.commit_results.await_args.kwargs
    assert sorted(item["track"] for item in submitted["recall_files"]) == ["memory", "skill"]
    assert submitted["resource"] == [{"path": "/synthetic/notes.md", "description": "project notes"}]


@pytest.mark.parametrize("only", ["skill", "all", "", False, []])
async def test_invalid_prepare_selection_does_not_write_or_read(tmp_path: Path, backend: Any, only: Any) -> None:
    workspace = MemorizeWorkspace(tmp_path / "workspace")

    with pytest.raises(ValueError):
        await prepare_memorize(_session(), workspace, backend, verify_command="offline-verify", only=only)

    assert not workspace.base.exists()
    backend.list_all_recall_files.assert_not_awaited()
    backend.commit_results.assert_not_awaited()


@pytest.mark.parametrize("selection", ["skill", "", None, [], {}])
async def test_unknown_marker_selection_preserves_run_without_submitting(
    tmp_path: Path, backend: Any, selection: Any
) -> None:
    workspace = MemorizeWorkspace(tmp_path / "workspace")
    await prepare_memorize(_session(), workspace, backend, verify_command="offline-verify", only="memory")
    _write_memory(workspace)
    marker = json.loads(workspace.active_run.read_text(encoding="utf-8"))
    marker["evolve_selection"] = selection
    workspace.active_run.write_text(json.dumps(marker), encoding="utf-8")
    before = _files(workspace.base)

    with pytest.raises(ValueError):
        await commit_memorize(workspace, backend)

    assert _files(workspace.base) == before
    backend.commit_results.assert_not_awaited()


async def test_memory_only_failed_commit_retries_with_same_selection(tmp_path: Path, backend: Any) -> None:
    workspace = MemorizeWorkspace(tmp_path / "workspace")
    await prepare_memorize(_session(), workspace, backend, verify_command="offline-verify", only="memory")
    _write_memory(workspace)
    workspace.skill.mkdir()
    (workspace.skill / "ignored.md").write_bytes(b"\xff")
    before = _files(workspace.base)
    backend.commit_results.side_effect = RuntimeError("store unavailable")

    with pytest.raises(RuntimeError, match="store unavailable"):
        await commit_memorize(workspace, backend)

    assert _files(workspace.base) == before
    backend.commit_results.side_effect = None
    await commit_memorize(workspace, backend)
    assert backend.commit_results.await_count == 2
    for call in backend.commit_results.await_args_list:
        assert [item["track"] for item in call.kwargs["recall_files"]] == ["memory"]
        assert call.kwargs["resource"] == []
    assert not workspace.active_run.exists()


async def test_memory_only_acknowledged_commit_cannot_be_retried(
    tmp_path: Path, backend: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = MemorizeWorkspace(tmp_path / "workspace")
    await prepare_memorize(_session(), workspace, backend, verify_command="offline-verify", only="memory")
    _write_memory(workspace)

    def fail_cleanup(*_args: Any) -> None:
        msg = "filesystem busy"
        raise PermissionError(msg)

    with monkeypatch.context() as patch:
        patch.setattr(lifecycle, "snapshot_tracked", fail_cleanup)
        with pytest.raises(RuntimeError, match="committed, but cleanup failed"):
            await commit_memorize(workspace, backend)

    marker = json.loads(workspace.active_run.read_text(encoding="utf-8"))
    assert marker["evolve_selection"] == "memory"
    assert marker["status"] == "committed"
    with pytest.raises(RuntimeError, match="already committed"):
        await commit_memorize(workspace, backend)
    backend.commit_results.assert_awaited_once()


def test_cli_memory_only_handoff_and_commit_cleanup(
    tmp_path: Path, backend: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "developer"
    payload = tmp_path / "session.json"
    payload.write_text(_session().model_dump_json(), encoding="utf-8")
    output: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "MEMORIZE_WORKSPACE", str(root))
    monkeypatch.setattr(cli, "_build_backend", lambda _args: backend)
    monkeypatch.setattr(cli, "_print_json", output.append)

    assert cli.main(["memorize", "prepare", str(payload), "--only", "memory", "--json"]) == 0
    prepared = output[-1]
    assert len(prepared["jobs"]) == 1
    assert sorted(prepared["transcript"]) == ["memory_path", "skill_path"]
    assert all(Path(path).is_file() for path in prepared["transcript"].values())
    assert prepared["next_command"] == f"memu memorize commit {prepared['run_id']}"
    workspace = MemorizeWorkspace(Path(prepared["workspace"]))
    _write_memory(workspace)
    workspace.skill.mkdir()
    (workspace.skill / "ignored.md").write_bytes(b"\xff")
    workspace.resources.write_bytes(b"\xff")

    assert cli.main(["memorize", "commit", prepared["run_id"], "--json"]) == 0

    assert [item["track"] for item in backend.commit_results.await_args.kwargs["recall_files"]] == ["memory"]
    assert backend.commit_results.await_args.kwargs["resource"] == []
    assert not workspace.base.exists()


@pytest.mark.parametrize(
    "argv",
    [
        ["memorize", "prepare", "session.json", "--only", "skill"],
        ["memorize", "commit", "run-test", "--only", "memory"],
    ],
)
def test_cli_rejects_unsupported_or_changed_selection(argv: list[str]) -> None:
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(argv)


@pytest.mark.parametrize("provider", ["inmemory", "sqlite"])
async def test_memory_only_updates_real_store_without_changing_unselected_records(
    tmp_path: Path, provider: str
) -> None:
    class FakeEmbedding:
        async def embed(self, inputs: list[str]) -> tuple[list[list[float]], None]:
            return [[1.0, 0.5, 0.25, 0.125] for _ in inputs], None

    service = MemoryService(
        database_config={"metadata_store": {"provider": provider, "dsn": f"sqlite:///{tmp_path}/memu.sqlite3"}}
    )
    service._embedding_pool._cache["embedding"] = FakeEmbedding()
    try:
        seeded = await service.commit_results(
            recall_files=[
                {
                    "track": "memory",
                    "name": "profile",
                    "description": "user preferences",
                    "content": "Original preference.",
                },
                {"track": "skill", "name": "deploy", "description": "deployment steps", "content": "Original steps."},
            ],
            resource=[{"path": "/synthetic/notes.md", "description": "Original notes."}],
        )
        original_skill = next(item for item in seeded["recall_files"] if item["track"] == "skill")
        original_resources = {
            resource_id: resource.model_dump()
            for resource_id, resource in service.database.resource_repo.list_resources().items()
        }
        workspace = MemorizeWorkspace(tmp_path / "workspace")
        await prepare_memorize(_session(), workspace, service, verify_command="offline-verify", only="memory")
        _write_memory(workspace, "profile")
        workspace.skill.mkdir()
        (workspace.skill / "deploy.md").write_text(
            "---\nname: deploy\ndescription: deployment steps\n---\nThis change must be ignored.\n", encoding="utf-8"
        )
        workspace.resources.write_text(
            "---\npath: /synthetic/notes.md\ndescription: This change must be ignored.\n---\n", encoding="utf-8"
        )

        committed = await commit_memorize(workspace, service)

        assert [(item["track"], item["name"]) for item in committed["recall_files"]] == [("memory", "profile")]
        assert committed["resources"] == []
        listed = (await service.list_all_recall_files())["recall_files"]
        assert next(item for item in listed if item["track"] == "skill") == original_skill
        assert next(item for item in listed if item["track"] == "memory")["content"] == "Use concise explanations."
        assert {
            resource_id: resource.model_dump()
            for resource_id, resource in service.database.resource_repo.list_resources().items()
        } == original_resources
    finally:
        service.database.close()
