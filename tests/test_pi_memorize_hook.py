from __future__ import annotations

import io
import json
import os
import shlex
import sys

import pytest

from memu.hosts import host_cli
from memu.hosts.bridging import Layout, pipeline
from memu.hosts.pi import cli, memorize_hook


def test_settled_launch_is_detached_and_forwards_active_model(tmp_path, monkeypatch, capsys):
    session = tmp_path / "sessions/2026_uuid.jsonl"
    session.parent.mkdir()
    session.write_text("{}\n", encoding="utf-8")
    monkeypatch.delenv("MEMU_BRIDGING_RUN", raising=False)
    monkeypatch.setattr(memorize_hook.shutil, "which", lambda _: "pi.cmd")
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps({
                "hook_event_name": "agent_settled",
                "session_file": str(session),
                "provider": "test",
                "model": "luna",
            })
        ),
    )
    calls = []
    monkeypatch.setattr(memorize_hook.subprocess, "Popen", lambda *a, **k: calls.append((a, k)))
    assert cli.main(["memorize-hook", "--base-dir", str(tmp_path / "base")]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["log_path"].endswith(".log")
    (argv,), kwargs = calls[0]
    assert argv[argv.index("--session-dir") + 1] == str(session.parent.resolve())
    assert argv[-4:] == ["--provider", "test", "--model", "luna"]
    assert kwargs["stdin"] == memorize_hook.subprocess.DEVNULL
    assert kwargs["stdout"] == kwargs["stderr"] == memorize_hook.subprocess.DEVNULL


@pytest.mark.parametrize(
    "payload,guard",
    [
        ({"hook_event_name": "agent_settled"}, ""),
        ({"hook_event_name": "agent_settled", "session_file": "not-used"}, "1"),
    ],
)
def test_ephemeral_and_worker_sessions_do_not_launch(tmp_path, monkeypatch, capsys, payload, guard):
    monkeypatch.setenv("MEMU_BRIDGING_RUN", guard)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(memorize_hook, "launch_background", lambda *a: pytest.fail("must not launch"))
    assert cli.main(["memorize-hook", "--base-dir", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out) == {}


def test_pi_agent_uses_native_prompt_argument(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(memorize_hook.worker, "stream_agent", lambda *a, **k: calls.append((a, k)))
    layout = Layout.default("pi", tmp_path)
    memorize_hook.stream_agent(["pi", "-p"], layout, "Process the job directory", 60)
    args, kwargs = calls[0]
    assert args == (["pi", "-p", "Process the job directory"], layout, "", 60)
    assert kwargs["stdin"] == memorize_hook.subprocess.DEVNULL


@pytest.mark.parametrize("failure", [False, True])
def test_pi_hook_runs_pipeline_with_guard_and_cooldown(tmp_path, monkeypatch, failure):
    sessions = tmp_path / "source"
    sessions.mkdir()
    (sessions / "2026_foreground.jsonl").write_text(
        json.dumps({
            "type": "message",
            "id": "u1",
            "message": {"role": "user", "content": "Remember my test project convention"},
        })
        + "\n",
        encoding="utf-8",
    )
    base = tmp_path / "base"
    layout = Layout.default("pi", base)
    monkeypatch.setenv("PI_SESSION_ID", "foreground")
    monkeypatch.delenv("MEMU_BRIDGING_RUN", raising=False)
    monkeypatch.setattr(host_cli, "_refresh_retrieval", lambda _: None)
    monkeypatch.setattr(host_cli.events, "flush", lambda: None)
    committed = []

    class Backend:
        async def list_all_recall_files(self, **kwargs):
            return {"recall_files": [], "next_cursor": None}

        async def commit_results(self, **kwargs):
            committed.append(kwargs)
            return {"recall_files": kwargs["recall_files"], "resources": []}

    monkeypatch.setattr(pipeline, "build_agentic_memory_backend_from_env", Backend)
    evolved = []

    def evolve(*args, **kwargs):
        assert os.environ["MEMU_BRIDGING_RUN"] == "1"
        assert os.environ["PI_SESSION_ID"] != "foreground"
        assert layout.session_manifest_pending.exists()
        assert not layout.session_manifest.exists()
        resource_job = (layout.jobs / "3.txt").read_text(encoding="utf-8")
        command = next(line.strip() for line in resource_job.splitlines() if " verify-resources " in line)
        assert shlex.split(command)[1:] == ["verify-resources", "--base-dir", str(base)]
        evolved.append(True)
        if failure:
            raise RuntimeError("agent failed")  # noqa: TRY003
        (layout.memory / "convention.md").write_text(
            "---\nname: convention\ndescription: test project convention\n---\nTest project uses complete sentences.\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(host_cli.hooks, "run_agent", evolve)
    args = ["hook-run", "--base-dir", str(base), "--session-dir", str(sessions), "--agent", "pi"]
    assert cli.main(args) == int(failure)
    assert bool(committed) is not failure
    assert layout.session_manifest.exists() is not failure
    assert layout.session_manifest_pending.exists() is failure
    assert os.environ["PI_SESSION_ID"] == "foreground"
    assert "MEMU_BRIDGING_RUN" not in os.environ
    assert cli.main(args) == 0
    assert len(evolved) == 1
