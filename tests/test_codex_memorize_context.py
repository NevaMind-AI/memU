import asyncio
import io
import json
import sys

import pytest

from memu.hosts.codex import hook_status, memorize_hook, notify_console


@pytest.mark.parametrize("status", ["started", "busy", "cooldown", "succeeded", "failed", "worker_started"])
def test_submit_injects_own_worker_snapshot(tmp_path, monkeypatch, capsys, status):
    path = tmp_path / "own.log"
    path.write_text(
        "=== WORKER codex pid=1 ===\n"
        + ("=== COOLDOWN until=1800.0 ===\n" if status == "cooldown" else "")
        + (f"=== MEMORIZE status={status} ===\n" if status != "worker_started" else "")
    )
    monkeypatch.delenv("MEMU_CODEX_MEMORIZE", raising=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"hook_event_name":"UserPromptSubmit"}'))
    monkeypatch.setattr(notify_console, "launch_background", lambda *args: path)
    monkeypatch.setattr(hook_status.time, "time", lambda: 61)
    from types import SimpleNamespace

    ticks = iter([0, 0, 0.6])
    monkeypatch.setattr(memorize_hook, "time", SimpleNamespace(monotonic=lambda: next(ticks), sleep=lambda _: None))
    args = memorize_hook.argparse.Namespace(
        base_dir=str(tmp_path), agent="unused", session_dir="unused", codex_home=None
    )
    assert asyncio.run(memorize_hook._cmd_memorize_hook(args)) == 0
    context = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    snapshot = json.loads(context.split("\n", 1)[1])
    assert snapshot["status"] == status
    assert snapshot["log"] == str(path)
    assert snapshot["observed_at"]
    assert "do not proactively announce" in context
    if status == "cooldown":
        assert snapshot["cooldown_remaining_minutes"] == 29


@pytest.mark.parametrize("now,minutes", [(0, 30), (1, 30), (60, 29), (1799, 1), (1800, 0), (1801, 0)])
def test_status_minutes_count_down(tmp_path, monkeypatch, now, minutes):
    log = tmp_path / "worker.log"
    log.write_text("=== COOLDOWN until=1800.0 ===\n=== MEMORIZE status=cooldown ===\n")
    monkeypatch.setattr(hook_status.time, "time", lambda: now)
    assert hook_status.memorize_status(log)["cooldown_remaining_minutes"] == minutes


def test_background_launch_returns_exact_worker_log(tmp_path, monkeypatch):
    from memu.hosts.bridging import Layout

    commands = []
    monkeypatch.setattr(notify_console.subprocess, "Popen", lambda command, **_: commands.append(command))
    path = notify_console.launch_background(
        ["hook-run", "--base-dir", str(tmp_path)], Layout(tmp_path, "codex"), "codex"
    )
    assert path.is_file()
    assert commands[0][commands[0].index("--log-path") + 1] == str(path)


def test_worker_writes_to_announced_log(tmp_path, monkeypatch):
    from memu.hosts.codex import cli

    path = notify_console._new_log_path(tmp_path)

    def run(_):
        print("=== MEMORIZE status=started ===", flush=True)
        return 0

    monkeypatch.setattr(cli, "main", run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "worker",
            "--label",
            "test",
            "--background",
            "--log-path",
            str(path),
            "--",
            "hook-run",
            "--base-dir",
            str(tmp_path),
        ],
    )
    assert notify_console.main() == 0
    assert hook_status.memorize_status(path)["status"] == "started"
    assert list((tmp_path / "log/hooks/memorize").glob("*.log")) == [path]
