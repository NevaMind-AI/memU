"""Claude Submit launches quickly; admitted workers own the complete pipeline."""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from uuid import UUID

import pytest

from memu.hosts import hooks, host_cli
from memu.hosts.bridging import Layout, pipeline, self_sessions
from memu.hosts.claude_code import cli
from memu.hosts.claude_code import memorize_hook as hook
from memu.hosts.hooks import admission


@pytest.mark.parametrize("platform", ["win32", "darwin", "linux"])
def test_submit_detaches_without_frontend_session(tmp_path, monkeypatch, capsys, platform):
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setattr(subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "foreground-session")
    monkeypatch.setenv("CLAUDECODE", "frontend")
    monkeypatch.delenv(hook.BACKGROUND_ENV, raising=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"hook_event_name":"UserPromptSubmit"}'))
    calls = []
    monkeypatch.setattr(hook.subprocess, "Popen", lambda *a, **k: calls.append((a, k)))
    assert (
        cli.main([
            "memorize-hook",
            "--base-dir",
            str(tmp_path),
            "--agent",
            "claude",
            "--session-dir",
            "synthetic-sessions",
        ])
        == 0
    )
    assert json.loads(capsys.readouterr().out) == {}
    (argv,), kwargs = calls[0]
    assert argv[:4] == [sys.executable, "-u", "-m", "memu.hosts.claude_code.memorize_hook"]
    assert "CLAUDE_CODE_SESSION_ID" not in kwargs["env"]
    assert "CLAUDECODE" not in kwargs["env"]
    assert kwargs["creationflags"] == (0x08000000 if platform == "win32" else 0)
    assert kwargs["start_new_session"] == (platform != "win32")
    assert all(kwargs[name] == subprocess.DEVNULL for name in ("stdin", "stdout", "stderr"))
    assert len(list((tmp_path / "log/hooks/memorize").glob("*.log"))) == 1
    assert os.environ["CLAUDE_CODE_SESSION_ID"] == "foreground-session"


@pytest.mark.parametrize(
    "event", ["{broken", "[]", '{"hook_event_name":"Stop"}', '{"hook_event_name":"UserPromptSubmit"}']
)
def test_invalid_event_or_recursion_never_launches(tmp_path, monkeypatch, capsys, event):
    monkeypatch.setenv(hook.BACKGROUND_ENV, "1")
    monkeypatch.setattr(sys, "stdin", io.StringIO(event))
    monkeypatch.setattr(hook, "launch_background", lambda _: pytest.fail("must not launch"))
    assert cli.main(["memorize-hook", "--agent", "claude", "--base-dir", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out) == {}


def test_launch_failure_fails_open(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv(hook.BACKGROUND_ENV, raising=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"hook_event_name":"UserPromptSubmit"}'))

    def fail(_):
        raise OSError("synthetic launch failure")  # noqa: TRY003

    monkeypatch.setattr(hook, "launch_background", fail)
    assert cli.main(["memorize-hook", "--agent", "claude", "--base-dir", str(tmp_path)]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out) == {}
    assert "synthetic launch failure" in output.err


def test_agent_receives_fresh_session_and_guard_before_start(tmp_path, monkeypatch):
    monkeypatch.setenv(hook.SESSION_ENV, "foreground-session")
    monkeypatch.setenv("CLAUDECODE", "frontend")
    monkeypatch.delenv(hook.BACKGROUND_ENV, raising=False)
    layout = Layout.default("claude-code", tmp_path)
    calls = []

    def stream(argv, layout, prompt, timeout, *, env):
        session_id = argv[-1]
        assert argv[-2] == "--session-id"
        assert str(UUID(session_id)) == session_id
        assert session_id != "foreground-session"
        assert session_id in self_sessions.load(layout.self_sessions)
        assert env[hook.SESSION_ENV] == session_id
        assert env[hook.BACKGROUND_ENV] == "1"
        assert "CLAUDECODE" not in env
        assert "memu-claude-code prepare or commit" in prompt
        calls.append(argv)

    monkeypatch.setattr(hook.worker, "stream_agent", stream)
    with hook.memorize_run(layout) as admitted:
        assert admitted
        hooks.run_agent(cli.SPEC.hook.agent, layout, executable="claude", stream_output=hook.stream_agent)
    assert len(calls) == 1
    assert self_sessions.load(layout.self_sessions) != ["foreground-session"]
    assert os.environ[hook.SESSION_ENV] == "foreground-session"
    assert hook.BACKGROUND_ENV not in os.environ


@pytest.mark.parametrize("failure", ["none", "agent", "commit"])
def test_code_submit_consumes_cowork_and_only_promotes_after_success(tmp_path, monkeypatch, failure):
    base = tmp_path / "workspace"
    sessions = tmp_path / "projects"
    project = sessions / "synthetic-project"
    project.mkdir(parents=True)
    foreground = project / "foreground-session.jsonl"
    foreground.write_text(
        json.dumps({"type": "user", "message": {"role": "user", "content": "user conversation"}}) + "\n"
    )
    root = tmp_path / "cowork"
    audit = root / "local-agent-mode-sessions/account/org/local_synthetic/audit.jsonl"
    audit.parent.mkdir(parents=True)
    shutil.copyfile(Path(__file__).parent / "fixtures/cowork/audit.jsonl", audit)
    monkeypatch.setenv("MEMU_COWORK_ROOTS", str(root))
    monkeypatch.setenv(hook.SESSION_ENV, "foreground-session")
    monkeypatch.delenv(hook.BACKGROUND_ENV, raising=False)
    monkeypatch.setattr(host_cli, "_refresh_retrieval", lambda _: None)
    monkeypatch.setattr(admission.time, "time", lambda: 36000.0)
    layout = Layout.default("claude-code", base)
    committed = []
    evolved = []

    class Backend:
        async def list_all_recall_files(self, **_):
            return {"recall_files": [], "next_cursor": None}

        async def commit_results(self, **kwargs):
            if failure == "commit":
                raise RuntimeError("synthetic commit failure")  # noqa: TRY003
            committed.append(kwargs)
            return {"recall_files": kwargs["recall_files"], "resources": []}

    monkeypatch.setattr(pipeline, "build_agentic_memory_backend_from_env", Backend)

    def evolve(*_, **kwargs):
        assert layout.session_manifest_pending.exists()
        assert not layout.session_manifest.exists()
        slices = "\n".join(path.read_text(encoding="utf-8") for path in layout.sessions.glob("*.jsonl"))
        assert "user conversation" in slices
        assert "plan the project" in slices
        session_id = os.environ[hook.SESSION_ENV]
        assert session_id != "foreground-session"
        assert session_id in self_sessions.load(layout.self_sessions)
        assert "foreground-session" not in self_sessions.load(layout.self_sessions)
        # Simulate the worker and its subagent being logged while evolve runs.
        for path in [project / f"{session_id}.jsonl", project / session_id / "subagents/agent-synthetic.jsonl"]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({"type": "user", "message": {"role": "user", "content": "worker bookkeeping"}}) + "\n"
            )
        evolved.append(slices)
        if failure == "agent":
            raise RuntimeError("synthetic agent failure")  # noqa: TRY003
        (layout.memory / "synthetic.md").write_text(
            "---\nname: synthetic\ndescription: test\n---\nmemory", encoding="utf-8"
        )

    monkeypatch.setattr(host_cli.hooks, "run_agent", evolve)
    argv = ["hook-run", "--base-dir", str(base), "--session-dir", str(sessions), "--agent", "unused"]
    assert cli.main(argv) == (0 if failure == "none" else 1)
    assert len(evolved) == 1
    assert layout.session_manifest.exists() is (failure == "none")
    assert layout.session_manifest_pending.exists() is (failure != "none")
    assert bool(committed) is (failure == "none")
    assert os.environ[hook.SESSION_ENV] == "foreground-session"
    # Every admitted outcome consumes cooldown; skips must preserve pending work.
    assert cli.main(argv) == 0
    assert len(evolved) == 1
    if failure == "none":
        monkeypatch.setattr(admission.time, "time", lambda: 37800.0)
        monkeypatch.setattr(host_cli.hooks, "run_agent", lambda *a, **k: pytest.fail("no new user turns"))
        assert cli.main(argv) == 0
        assert len(committed) == 2
        assert not list(layout.jobs.glob("*.txt"))
        with audit.open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps({
                    "type": "user",
                    "timestamp": "2026-08-14T09:01:00Z",
                    "uuid": "user-increment",
                    "message": {"role": "user", "content": "new Cowork increment"},
                })
                + "\n"
            )

        def evolve_increment(*_, **kwargs):
            slices = "\n".join(path.read_text(encoding="utf-8") for path in layout.sessions.glob("*.jsonl"))
            assert "new Cowork increment" in slices
            assert "plan the project" not in slices
            assert "user conversation" not in slices
            assert "worker bookkeeping" not in slices
            evolved.append(slices)

        # A submission during cooldown preserves the new audit for the next admitted pass.
        assert cli.main(argv) == 0
        assert len(evolved) == 1
        monkeypatch.setattr(admission.time, "time", lambda: 39600.0)
        monkeypatch.setattr(host_cli.hooks, "run_agent", evolve_increment)
        assert cli.main(argv) == 0
        assert len(evolved) == 2
        assert len(committed) == 3


def test_real_agent_process_skips_both_submit_handlers(tmp_path, monkeypatch):
    monkeypatch.setenv(hook.SESSION_ENV, "foreground-session")
    monkeypatch.delenv(hook.BACKGROUND_ENV, raising=False)
    layout = Layout.default("claude-code", tmp_path)
    script = """
import io, json, os, sys
from memu.hosts.claude_code.cli import main
base = sys.argv[1]
assert sys.argv[2:] == ['--session-id', os.environ['CLAUDE_CODE_SESSION_ID']]
assert os.environ['MEMU_CLAUDE_MEMORIZE'] == '1'
assert os.environ['CLAUDE_CODE_SESSION_ID'] != 'foreground-session'
assert 'CLAUDECODE' not in os.environ
for command in [['memorize-hook', '--agent', 'must-not-run'], ['prompt-hook']]:
    sys.stdin = io.StringIO(json.dumps({'hook_event_name': 'UserPromptSubmit', 'prompt': 'synthetic'}))
    assert main([*command, '--base-dir', base]) == 0
print('both handlers skipped')
"""
    with hook.memorize_run(layout) as admitted:
        assert admitted
        hook.stream_agent([sys.executable, "-c", script, str(tmp_path)], layout, "synthetic job", 10)
    logs = list((tmp_path / "log/hooks/memorize").glob("*.log"))
    assert "both handlers skipped" in logs[0].read_text(encoding="utf-8")
    trace = json.loads(next((tmp_path / "log/hooks/retrieve").glob("*.json")).read_text(encoding="utf-8"))
    assert trace["status"] == "self_run_skipped"


def test_real_detached_worker_records_failure_without_touching_store(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv(hook.BACKGROUND_ENV, raising=False)
    monkeypatch.setenv("MEMU_COWORK_ROOTS", "")
    monkeypatch.setenv(hook.SESSION_ENV, "foreground-session")
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"hook_event_name":"UserPromptSubmit"}'))
    assert (
        cli.main([
            "memorize-hook",
            "--base-dir",
            str(tmp_path),
            "--session-dir",
            str(tmp_path / "missing"),
            "--agent",
            "unused",
        ])
        == 0
    )
    assert json.loads(capsys.readouterr().out) == {}
    log = next((tmp_path / "log/hooks/memorize").glob("*.log"))
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        text = log.read_text(encoding="utf-8")
        if "FINISHED claude-code exit=" in text:
            break
        time.sleep(0.01)
    assert "FINISHED claude-code exit=2" in text
    assert "MEMORIZE status=failed" in text
    assert not (tmp_path / ".session_manifest.claude-code.json").exists()
    assert not (tmp_path / ".memorize_last_started.codex.json").exists()


def test_busy_claude_worker_never_prepares(tmp_path, monkeypatch):
    async def forbidden(*_):
        pytest.fail("busy worker must not prepare")

    monkeypatch.setattr(host_cli, "_cmd_prepare", forbidden)
    with admission.workspace_lock(tmp_path) as acquired:
        assert acquired
        assert cli.main(["hook-run", "--base-dir", str(tmp_path)]) == 0
    assert not (tmp_path / ".memorize_last_started.claude-code.json").exists()


def test_worker_logs_complete_pipeline_result(tmp_path, monkeypatch, capsys):
    log = tmp_path / "worker.log"
    args = [
        "worker",
        "--base-dir",
        str(tmp_path),
        "--session-dir",
        "sessions",
        "--agent",
        "unused",
        "--log-path",
        str(log),
    ]
    monkeypatch.setattr(sys, "argv", args)

    def run(argv):
        assert argv[0] == "hook-run"
        print("synthetic worker output 😀")
        return 2

    monkeypatch.setattr(cli, "main", run)
    assert hook.main() == 2
    assert not capsys.readouterr().out
    text = log.read_text(encoding="utf-8")
    assert "synthetic worker output 😀" in text
    assert "MEMORIZE status=failed" in text
    assert "FINISHED claude-code exit=2" in text
