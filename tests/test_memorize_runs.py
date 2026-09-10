from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from memu import cli


@pytest.fixture()
def rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "developer"
    payload = tmp_path / "session.json"
    payload.write_text(
        json.dumps({"items": [{"type": "message", "role": "user", "content": "Remember this"}]}), encoding="utf-8"
    )
    backend = SimpleNamespace(
        list_all_recall_files=AsyncMock(return_value={"recall_files": [], "next_cursor": None}),
        commit_results=AsyncMock(return_value={"recall_files": [], "resources": []}),
    )
    output: list[dict] = []
    monkeypatch.setattr(cli, "MEMORIZE_WORKSPACE", str(root))
    monkeypatch.setattr(cli, "_build_backend", lambda _args: backend)
    monkeypatch.setattr(cli, "_print_json", output.append)
    monkeypatch.setattr("memu.hosts.templates.resolve", lambda _name, embedded: embedded)
    return root, payload, backend, output


async def test_concurrent_prepares_isolate_batches_and_commit_only_their_run(rig) -> None:
    root, payload, backend, output = rig
    barrier = asyncio.Barrier(2)

    async def list_files(**_kwargs):
        await barrier.wait()
        return {"recall_files": [], "next_cursor": None}

    backend.list_all_recall_files.side_effect = list_files
    parser = cli.build_parser()
    args = parser.parse_args(["memorize", "prepare", str(payload), str(payload), "--json"])
    results = await asyncio.wait_for(
        asyncio.gather(cli._cmd_memorize_prepare(args), cli._cmd_memorize_prepare(args)), timeout=5
    )
    assert results == [0, 0]
    first, second = output
    assert first["run_id"] != second["run_id"]
    for prepared in (first, second):
        workspace = Path(prepared["workspace"])
        assert workspace.parent == root / "runs"
        assert len(prepared["transcripts"]) == 2
        assert len(prepared["jobs"]) == 5
        assert (workspace / ".memorize_run.json").is_file()
        assert f"memu memorize verify-resources {prepared['run_id']}" in Path(prepared["jobs"][-1]).read_text(
            encoding="utf-8"
        )
        (workspace / "executor-note.txt").write_text("temporary", encoding="utf-8")

    second_files = {
        p.relative_to(second["workspace"]): p.read_bytes() for p in Path(second["workspace"]).rglob("*") if p.is_file()
    }
    await cli._cmd_memorize_commit(parser.parse_args(["memorize", "commit", first["run_id"], "--json"]))
    assert not Path(first["workspace"]).exists()
    assert {
        p.relative_to(second["workspace"]): p.read_bytes() for p in Path(second["workspace"]).rglob("*") if p.is_file()
    } == second_files
    backend.commit_results.assert_awaited_once()


def test_failed_commit_preserves_every_file_and_can_retry(rig) -> None:
    _root, payload, backend, output = rig
    assert cli.main(["memorize", "prepare", str(payload), "--json"]) == 0
    prepared = output[-1]
    workspace = Path(prepared["workspace"])
    (workspace / "memory").mkdir()
    (workspace / "memory" / "note.md").write_text("---\nname: note\n---\nremember me", encoding="utf-8")
    before = {p.relative_to(workspace): p.read_bytes() for p in workspace.rglob("*") if p.is_file()}
    backend.commit_results.side_effect = RuntimeError("store unavailable")

    assert cli.main(["memorize", "commit", prepared["run_id"], "--json"]) == 1
    assert {p.relative_to(workspace): p.read_bytes() for p in workspace.rglob("*") if p.is_file()} == before
    backend.commit_results.side_effect = None
    assert cli.main(["memorize", "commit", prepared["run_id"], "--json"]) == 0
    assert not workspace.exists()
    assert backend.commit_results.call_args.kwargs["recall_files"][0]["name"] == "note"


def test_discard_removes_only_selected_run_without_backend(rig, monkeypatch: pytest.MonkeyPatch) -> None:
    root, payload, _backend, output = rig
    for _ in range(2):
        assert cli.main(["memorize", "prepare", str(payload), "--json"]) == 0
    first, second = output
    # An incomplete run from an interrupted prepare is also explicitly discardable.
    (Path(first["workspace"]) / ".memorize_run.json").unlink()
    sentinel = root / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    monkeypatch.setattr(cli, "_build_backend", lambda _args: pytest.fail("discard must not build a backend"))
    assert cli.main(["memorize", "discard", first["run_id"], "--json"]) == 0
    assert output[-1] == {"run_id": first["run_id"], "discarded": True}
    assert not Path(first["workspace"]).exists()
    assert Path(second["workspace"]).is_dir()
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_commit_cleanup_failure_reports_durable_success(
    rig, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _root, payload, backend, output = rig
    assert cli.main(["memorize", "prepare", str(payload), "--json"]) == 0
    prepared = output[-1]
    workspace = Path(prepared["workspace"])

    def fail_cleanup(_path):
        msg = "directory busy"
        raise PermissionError(msg)

    with monkeypatch.context() as patch:
        patch.setattr(cli.shutil, "rmtree", fail_cleanup)
        assert cli.main(["memorize", "commit", prepared["run_id"]]) == 1
    assert "committed, but cleanup failed" in capsys.readouterr().err
    backend.commit_results.assert_awaited_once()
    assert not (workspace / ".memorize_run.json").exists()
    assert cli.main(["memorize", "discard", prepared["run_id"]]) == 0
    assert not workspace.exists()


def test_invalid_batch_does_not_allocate_a_run(rig) -> None:
    root, payload, backend, _output = rig
    invalid = payload.with_name("invalid.json")
    invalid.write_text('{"items": []}', encoding="utf-8")
    assert cli.main(["memorize", "prepare", str(payload), str(invalid)]) == 1
    assert not root.exists()
    backend.list_all_recall_files.assert_not_awaited()


def test_failed_prepare_removes_only_its_new_directory(rig) -> None:
    root, payload, backend, output = rig
    assert cli.main(["memorize", "prepare", str(payload), "--json"]) == 0
    previous = Path(output[-1]["workspace"])
    backend.list_all_recall_files.side_effect = RuntimeError("list failed")
    assert cli.main(["memorize", "prepare", str(payload), "--json"]) == 1
    assert list((root / "runs").iterdir()) == [previous]
    assert (previous / ".memorize_run.json").is_file()


@pytest.mark.parametrize("action", ["commit", "verify-resources", "discard"])
@pytest.mark.parametrize("run_id", ["../runs", "/outside", "C:\\outside", "run-../other", "run-missing"])
def test_run_commands_reject_invalid_or_unknown_ids(
    rig, monkeypatch: pytest.MonkeyPatch, action: str, run_id: str
) -> None:
    root, _payload, _backend, _output = rig
    sentinel = root / "runs" / "run-keep"
    sentinel.mkdir(parents=True)
    monkeypatch.setattr(cli, "_build_backend", lambda _args: pytest.fail("invalid run must not build a backend"))
    assert cli.main(["memorize", action, run_id]) == 1
    assert sentinel.is_dir()


def test_run_commands_reject_symlink_directory(rig, tmp_path: Path) -> None:
    root, _payload, backend, _output = rig
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep", encoding="utf-8")
    link = root / "runs" / "run-link"
    link.parent.mkdir(parents=True)
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    for action in ("commit", "verify-resources", "discard"):
        assert cli.main(["memorize", action, "run-link"]) == 1
    assert (outside / "keep.txt").is_file()
    backend.commit_results.assert_not_awaited()


def test_verify_rejects_incomplete_run(rig) -> None:
    root, _payload, _backend, _output = rig
    (root / "runs" / "run-incomplete").mkdir(parents=True)
    assert cli.main(["memorize", "verify-resources", "run-incomplete"]) == 1
