"""Hermes automatic memorize admission and real worker session exclusion."""

from __future__ import annotations

import io
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from memu.hosts.bridging import Layout, self_sessions
from memu.hosts.bridging.transcripts import prepare_transcripts
from memu.hosts.hermes import hook, hook_install, memorize_hook
from memu.hosts.hermes.cli import main
from memu.hosts.hermes.sessions import HermesTranscriptSource


@pytest.mark.parametrize(
    "completed,failed,interrupted,known,expected",
    [
        (True, False, False, False, 1),
        (False, False, False, False, 0),
        (True, True, False, False, 0),
        (True, False, True, False, 0),
        (True, False, False, True, 0),
    ],
)
def test_end_hook_admission(tmp_path, monkeypatch, completed, failed, interrupted, known, expected):
    monkeypatch.delenv("MEMU_BRIDGING_RUN", raising=False)
    if known:
        self_sessions.remember(Layout.default("hermes", tmp_path).self_sessions, "worker")
    event = {
        "hook_event_name": "on_session_end",
        "session_id": "worker",
        "extra": {"completed": completed, "failed": failed, "interrupted": interrupted},
    }
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    calls = []

    def launch(*args):
        calls.append(args)
        return tmp_path / "log"

    monkeypatch.setattr(memorize_hook, "launch", launch)
    assert main(["memorize-hook", "--base-dir", str(tmp_path)]) == 0
    assert len(calls) == expected


def test_installed_shell_command_starts_detached_worker(tmp_path, monkeypatch):
    import os
    import shlex
    import time

    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "profile"))
    (tmp_path / "profile").mkdir()
    monkeypatch.delenv("MEMU_BRIDGING_RUN", raising=False)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_agent = bin_dir / ("hermes.exe" if sys.platform == "win32" else "hermes")
    fake_agent.write_text("#!/bin/sh\nexit 88\n", encoding="utf-8")
    fake_agent.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    config: dict[str, Any] = {}

    def command(*argv):
        if argv[:2] == ("config", "set"):
            config["on_session_end"] = json.loads(argv[3])
        if argv == ("hooks", "list"):
            return config["on_session_end"][0]["command"]
        return json.dumps(config)

    monkeypatch.setattr(hook_install, "command", command)
    base = tmp_path / "workspace"
    base.mkdir()
    (base / ".memorize_last_started.hermes.json").write_text(json.dumps(time.time()), encoding="utf-8")
    hook_install.configure_memorize(base)
    installed = config["on_session_end"][0]["command"]
    started = time.monotonic()
    result = subprocess.run(  # noqa: S603
        shlex.split(installed),
        input=json.dumps({
            "hook_event_name": "on_session_end",
            "session_id": "real-user",
            "extra": {"completed": True, "failed": False, "interrupted": False},
        }),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert time.monotonic() - started < 10
    log = Path(json.loads(result.stdout)["log_path"])
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and "=== FINISHED" not in log.read_text(encoding="utf-8"):
        time.sleep(0.05)
    text = log.read_text(encoding="utf-8")
    assert "=== WORKER hermes" in text and "status=cooldown" in text and "exit=0" in text


def test_direct_worker_admission_preserves_user_identity(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_SESSION_ID", "user-session")
    monkeypatch.delenv("MEMU_BRIDGING_RUN", raising=False)
    layout = Layout.default("hermes", tmp_path)
    with memorize_hook.memorize_run(layout) as admitted:
        assert admitted
        assert "HERMES_SESSION_ID" not in memorize_hook.os.environ
        assert memorize_hook.os.environ["MEMU_BRIDGING_RUN"] == "1"
    assert memorize_hook.os.environ["HERMES_SESSION_ID"] == "user-session"
    assert "MEMU_BRIDGING_RUN" not in memorize_hook.os.environ
    assert self_sessions.load(layout.self_sessions) == []


def test_worker_launch_is_detached_and_drops_origin_identity(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_SESSION_ID", "real-user")
    monkeypatch.setattr(memorize_hook.shutil, "which", lambda _: "hermes")
    calls = []
    monkeypatch.setattr(memorize_hook.subprocess, "Popen", lambda *a, **k: calls.append((a, k)))
    log = memorize_hook.launch(tmp_path, "real-user")
    assert log.is_file()
    argv = calls[0][0][0]
    options = calls[0][1]
    assert argv[argv.index("--origin-session") + 1] == "real-user"
    assert "HERMES_SESSION_ID" not in options["env"]
    assert options["stdin"] == subprocess.DEVNULL and options["stdout"] == subprocess.DEVNULL


@pytest.mark.parametrize("ending", ["pass", "raise SystemExit(7)", "__import__('time').sleep(30)"])
def test_worker_id_is_excluded_in_second_round(tmp_path, monkeypatch, ending):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    layout = Layout.default("hermes", tmp_path / "workspace")
    db = tmp_path / "state.db"
    with sqlite3.connect(db) as c:
        c.executescript(
            "CREATE TABLE sessions (id TEXT PRIMARY KEY); CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT, tool_call_id TEXT, tool_calls TEXT, tool_name TEXT, timestamp REAL NOT NULL);"
        )
        c.execute("INSERT INTO messages(session_id,role,content,timestamp) VALUES ('user-1','user','USER_ONE',1)")
    source = HermesTranscriptSource(db)
    assert (
        prepare_transcripts(source, layout.sessions, layout.session_manifest, 10, layout.session_manifest_pending) == 1
    )
    layout.session_manifest.write_bytes(layout.session_manifest_pending.read_bytes())
    script = (
        "import sqlite3,json; "  # noqa: S608 -- Literal SQL; only the temporary database path is interpolated.
        f"c=sqlite3.connect({str(db)!r}); "
        "c.execute(\"INSERT INTO messages(session_id,role,content,timestamp) VALUES ('worker-real','user','WORKER_BOOKKEEPING',2)\"); "
        "c.execute(\"INSERT INTO messages(session_id,role,content,timestamp) VALUES ('user-2','user','USER_TWO',3)\"); "
        "c.commit(); c.close(); "
        "print('Session: worker-real',flush=True); "
        + ("" if "sleep" in ending else "print(json.dumps({'type':'result','session_id':'worker-real'}),flush=True); ")
        + ending
    )
    if ending == "pass":
        hook.stream_agent([sys.executable, "-c", script], layout, "jobs", 10)
    elif "sleep" in ending:
        with pytest.raises(subprocess.TimeoutExpired):
            hook.stream_agent([sys.executable, "-c", script], layout, "jobs", 1)
    else:
        with pytest.raises(RuntimeError, match="exited"):
            hook.stream_agent([sys.executable, "-c", script], layout, "jobs", 10)
    assert self_sessions.load(layout.self_sessions) == ["worker-real"]
    assert (
        prepare_transcripts(
            source,
            layout.sessions,
            layout.session_manifest,
            10,
            layout.session_manifest_pending,
            skip_sessions=self_sessions.load(layout.self_sessions),
        )
        == 1
    )
    assert "USER_TWO" in (layout.sessions / "1.jsonl").read_text()
    assert "WORKER_BOOKKEEPING" not in (layout.sessions / "1_full.jsonl").read_text()


def test_shell_hook_config_preserves_other_hooks_and_consent(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    other = {"command": "user-script", "timeout": 20}
    config: dict[str, Any] = {"on_session_end": [other], "post_tool_call": [other]}

    def command(*argv):
        if argv == ("hooks", "list"):
            return "\n".join(entry["command"] for entry in config.get("on_session_end", []))
        if argv[:2] == ("config", "set"):
            config["on_session_end"] = json.loads(argv[3])
        elif argv[:2] == ("config", "unset"):
            config.pop("on_session_end", None)
        return json.dumps(config)

    monkeypatch.setattr(hook_install, "command", command)
    consent = tmp_path / "shell-hooks-allowlist.json"
    consent.write_text(json.dumps({"approvals": [{"event": "on_session_end", "command": "user-script"}]}))
    for _ in range(2):
        hook_install.configure_memorize(tmp_path / "workspace")
        assert len(config["on_session_end"]) == 2
        assert len(json.loads(consent.read_text())["approvals"]) == 2
    hook_install.configure_memorize(None)
    assert config == {"on_session_end": [other], "post_tool_call": [other]}
    assert json.loads(consent.read_text())["approvals"] == [{"event": "on_session_end", "command": "user-script"}]
