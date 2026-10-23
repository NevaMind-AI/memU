"""Exercise private Codex runs through the real CLI and shared lifecycle."""

import json
import shlex
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from memu.hosts import host_cli
from memu.hosts.bridging import pipeline, runs
from memu.hosts.codex import cli, notify_console
from memu.run import RunWorkspace


@pytest.fixture
def rig(tmp_path, monkeypatch):
    base = tmp_path / "custom host with spaces"
    source = tmp_path / "source"
    source.mkdir()
    session = source / "rollout-2026-10-20T10-00-00-01a15738-c76e-7661-a46c-6e3126d0d81a.jsonl"
    session.write_text(json.dumps({"payload": {"type": "message", "role": "user", "content": "remember A"}}) + "\n")
    backend = SimpleNamespace(
        list_all_recall_files=AsyncMock(return_value={"recall_files": [], "next_cursor": None}),
        commit_results=AsyncMock(return_value={"recall_files": [], "resources": []}),
    )
    monkeypatch.setattr(pipeline, "build_agentic_memory_backend_from_env", lambda: backend)
    monkeypatch.setattr(host_cli, "_refresh_retrieval", lambda _: None)
    monkeypatch.setattr(host_cli.hooks, "run_agent", lambda *a, **k: None)

    def invoke(command, *args):
        argv = [command, "--base-dir", str(base), *args]
        if command in {"prepare", "hook-run"}:
            argv += ["--session-dir", str(source)]
        return cli.main(argv)

    def current():
        paths = list((base / "runs").iterdir())
        assert len(paths) == 1
        return runs.resolve(host_cli.Layout(base, "codex"), paths[0].name)

    return SimpleNamespace(base=base, source=source, session=session, backend=backend, invoke=invoke, current=current)


def test_hook_allocates_executes_commits_and_cleans_one_private_run(rig, monkeypatch):
    seen = []

    def evolve(_agent, layout, **_kwargs):
        assert isinstance(layout, RunWorkspace)
        assert layout.base.parent == rig.base / "runs"
        assert layout.state == rig.base
        assert list(layout.sessions.glob("*.jsonl"))
        assert len(list(layout.jobs.glob("*.txt"))) == 3
        assert layout.session_manifest_pending.is_file()
        assert not layout.session_manifest.exists()
        with notify_console._workspace_lock(rig.base) as acquired:
            assert not acquired
        resource = next(layout.jobs.glob("3.txt")).read_text(encoding="utf-8")
        command = host_cli._run_command(cli.SPEC, layout, "verify-resources")
        assert command in resource
        # Run the exact generated command, including its custom base and run id.
        with ThreadPoolExecutor() as pool:
            assert pool.submit(cli.main, shlex.split(command)[1:]).result(timeout=5) == 0
        (layout.memory / "note.md").write_text("---\nname: note\n---\nremember me", encoding="utf-8")
        seen.append(layout.base)

    monkeypatch.setattr(host_cli.hooks, "run_agent", evolve)
    assert rig.invoke("hook-run") == 0
    assert len(seen) == 1 and not seen[0].exists()
    assert not list((rig.base / "runs").iterdir())
    assert rig.backend.commit_results.await_args.kwargs["recall_files"][0]["name"] == "note"
    cursor = rig.base / ".session_manifest.codex.json"
    assert json.loads(cursor.read_text())[rig.session.name]["lines"] == 1
    assert not (rig.base / "jobs").exists()
    assert rig.invoke("hook-run") == 0  # cooldown creates no new run
    assert len(seen) == 1


def test_manual_run_blocks_new_claim_and_noop_promotes_cursor(rig):
    assert rig.invoke("prepare") == 0
    layout = rig.current()
    before = {p.relative_to(layout.base): p.read_bytes() for p in layout.base.rglob("*") if p.is_file()}
    assert rig.invoke("prepare") == 1
    assert rig.invoke("hook-run") == 1
    assert before == {p.relative_to(layout.base): p.read_bytes() for p in layout.base.rglob("*") if p.is_file()}
    assert rig.invoke("commit", "--run-id", layout.base.name) == 0
    assert not layout.base.exists()
    assert layout.session_manifest.is_file()
    assert rig.invoke("prepare") == 0
    empty = rig.current()
    assert not list(empty.jobs.glob("*.txt"))
    assert rig.invoke("commit", "--run-id", empty.base.name) == 0
    assert rig.backend.commit_results.await_count == 2


def test_evolve_failure_is_preserved_and_explicit_resume_reuses_input(rig, monkeypatch):
    attempts = []

    def evolve(_agent, layout, **_kwargs):
        attempts.append(layout.base)
        if len(attempts) == 1:
            raise RuntimeError("synthetic agent failure")  # noqa: TRY003

    monkeypatch.setattr(host_cli.hooks, "run_agent", evolve)
    assert rig.invoke("hook-run") == 1
    layout = rig.current()
    assert not layout.session_manifest.exists()
    assert runs.phase(layout) == "prepared"
    rig.backend.commit_results.assert_not_awaited()
    assert rig.invoke("hook-run", "--run-id", layout.base.name) == 0
    assert attempts == [layout.base, layout.base]
    assert not layout.base.exists()
    assert layout.session_manifest.is_file()


@pytest.mark.parametrize("stage", ["cursor", "cleanup", "directory", "partial_directory", "removed_directory"])
def test_acknowledged_commit_retries_only_local_finalization(rig, monkeypatch, stage):
    assert rig.invoke("prepare") == 0
    layout = rig.current()

    def fail(*_args, **_kwargs):
        raise PermissionError("synthetic finalization failure")  # noqa: TRY003

    with monkeypatch.context() as patch:
        if stage == "cursor":
            original = pipeline.os.replace

            def replace(src, dst):
                if Path(dst) == layout.session_manifest:
                    fail()
                return original(src, dst)

            patch.setattr(pipeline.os, "replace", replace)
        elif stage == "cleanup":
            patch.setattr(pipeline, "finish_run", fail)
        else:

            def remove(workspace):
                if stage == "partial_directory":
                    workspace.receipt.unlink()
                    (workspace.base / ".run.json").unlink()
                elif stage == "removed_directory":
                    import shutil

                    shutil.rmtree(workspace.base)
                fail()

            patch.setattr(host_cli, "discard_run", remove)
        assert rig.invoke("commit", "--run-id", layout.base.name) == 1
    assert layout.receipt.is_file() or runs.cleanup_pending(layout)
    rig.backend.commit_results.assert_awaited_once()
    monkeypatch.setattr(pipeline, "build_agentic_memory_backend_from_env", lambda: pytest.fail("local finalization"))
    monkeypatch.setattr(host_cli.hooks, "run_agent", lambda *a, **k: pytest.fail("receipt must skip evolve"))
    assert rig.invoke("hook-run", "--run-id", layout.base.name) == 0
    rig.backend.commit_results.assert_awaited_once()
    assert not layout.base.exists()
    assert layout.session_manifest.is_file()


def test_failed_backend_keeps_run_and_discard_leaves_input_selectable(rig):
    assert rig.invoke("prepare") == 0
    layout = rig.current()
    rig.backend.commit_results.side_effect = RuntimeError("synthetic backend failure")
    assert rig.invoke("commit", "--run-id", layout.base.name) == 1
    assert not layout.receipt.exists() and not layout.session_manifest.exists()
    assert rig.invoke("discard", "--run-id", layout.base.name) == 0
    assert rig.invoke("prepare") == 0
    retry = rig.current()
    assert "remember A" in (retry.sessions / "1.jsonl").read_text()


def test_incomplete_prepare_requires_discard_and_busy_preserves_run(rig):
    rig.backend.list_all_recall_files.side_effect = RuntimeError("synthetic mirror failure")
    assert rig.invoke("prepare") == 1
    layout = rig.current()
    assert runs.phase(layout) == "preparing"
    assert rig.invoke("commit", "--run-id", layout.base.name) == 1
    assert rig.invoke("hook-run", "--run-id", layout.base.name) == 1
    with notify_console._workspace_lock(rig.base) as acquired:
        assert acquired
        assert rig.invoke("discard", "--run-id", layout.base.name) == 1
        assert rig.invoke("prepare") == 1
    assert layout.base.exists()
    assert rig.invoke("discard", "--run-id", layout.base.name) == 0


def test_legacy_pending_work_requires_explicit_completion(rig):
    rig.base.mkdir()
    (rig.base / ".session_manifest.codex.json.pending").write_text('{"legacy":{"lines":1}}')
    assert rig.invoke("prepare") == 1
    assert rig.invoke("commit", "--run-id", "legacy") == 0
    assert json.loads((rig.base / ".session_manifest.codex.json").read_text()) == {"legacy": {"lines": 1}}
    assert rig.invoke("prepare") == 0


@pytest.mark.parametrize("action", ["commit", "verify-resources", "discard", "hook-run"])
@pytest.mark.parametrize("run_id", ["../outside", "C:\\outside", "run-missing"])
def test_invalid_run_does_not_reach_backend(rig, action, run_id):
    assert rig.invoke(action, "--run-id", run_id) == 1
    rig.backend.commit_results.assert_not_awaited()
    rig.backend.list_all_recall_files.assert_not_awaited()
