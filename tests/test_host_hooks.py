from __future__ import annotations

import subprocess

import pytest

from memu.hosts.bridging import Layout
from memu.hosts.codex import notify_console
from memu.hosts.hooks import CodexNotifyHook, HeadlessAgent, run_agent


def _patch_console_launcher(monkeypatch, launch):
    from dataclasses import replace

    from memu.hosts.codex import cli

    monkeypatch.setattr(cli, "SPEC", replace(cli.SPEC, hook=replace(cli.HOOK, launch_console=launch)))


def test_diagnostic_agent_output_is_live(tmp_path, capsys):
    import concurrent.futures
    import sys
    import time

    layout = Layout.default("codex", tmp_path)
    script = (
        "import sys,time,pathlib; sys.stdin.read(); "
        "print('agent stdout',flush=True); print('agent stderr',file=sys.stderr,flush=True); "
        "\nwhile not pathlib.Path('release').exists(): time.sleep(.01)"
    )
    with concurrent.futures.ThreadPoolExecutor() as pool:
        future = pool.submit(
            run_agent,
            HeadlessAgent((sys.executable, "-c", script), 10),
            layout,
            stream_output=notify_console.stream_agent,
        )
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                log = tmp_path / "hook.log"
                if log.exists() and "agent stderr" in log.read_text():
                    break
                time.sleep(0.01)
            assert "agent stdout" in log.read_text()
            assert "agent stderr" in log.read_text()
            assert not future.done()
        finally:
            (tmp_path / "release").touch()
        future.result(timeout=5)
    assert "agent stdout" in capsys.readouterr().out


@pytest.mark.parametrize(
    "script,timeout,error",
    [
        ("import sys; print('failure',flush=True); sys.exit(7)", 10, RuntimeError),
        ("import time; print('waiting',flush=True); time.sleep(30)", 1, subprocess.TimeoutExpired),
    ],
)
def test_diagnostic_agent_failure_and_timeout(tmp_path, script, timeout, error):
    import sys

    with pytest.raises(error):
        run_agent(
            HeadlessAgent((sys.executable, "-c", script), timeout),
            Layout.default("codex", tmp_path),
            stream_output=notify_console.stream_agent,
        )
    assert (tmp_path / "hook.log").read_text()


def test_hook_passes_diagnostic_options(tmp_path, monkeypatch):
    from memu.hosts.codex.cli import main

    calls = []
    _patch_console_launcher(monkeypatch, lambda *args: calls.append(args))
    assert (
        main([
            "hook",
            "--base-dir",
            str(tmp_path),
            "--session-dir",
            "~/sessions",
            "--diagnostic",
            "--hold",
            "--label",
            "desktop-codex",
            '{"turn-id":"test"}',
        ])
        == 0
    )
    argv, _layout, label, hold = calls[0]
    assert "--diagnostic" in argv
    assert argv[argv.index("--session-dir") + 1] == "~/sessions"
    assert label == "desktop-codex" and hold


@pytest.mark.parametrize("platform", ["win32", "darwin", "linux"])
def test_diagnostic_launch_platform(tmp_path, monkeypatch, platform):

    calls = []
    monkeypatch.setattr(notify_console.sys, "platform", platform)
    monkeypatch.setattr(notify_console.subprocess, "CREATE_NEW_CONSOLE", 16, raising=False)
    monkeypatch.setattr(notify_console.shutil, "which", lambda _: "/usr/bin/xterm")
    monkeypatch.setattr(notify_console.subprocess, "Popen", lambda *a, **k: calls.append((a, k)))
    monkeypatch.setattr(notify_console.subprocess, "run", lambda *a, **k: calls.append((a, k)))
    notify_console.launch(["hook-run", "--base-dir", str(tmp_path)], Layout.default("codex", tmp_path), "cli", True)
    args, kwargs = calls[0]
    assert ("creationflags" in kwargs) == (platform == "win32")
    assert "cmd.exe" not in args[0]
    worker = args[0] if platform == "win32" else args[0][-1] if platform == "darwin" else args[0][2:]
    assert "memu.hosts.codex.notify_console" in worker


def test_codex_notify_hook_installs_and_removes_its_own_command(tmp_path):
    config = tmp_path / "config.toml"
    hook = CodexNotifyHook(config)
    argv = ["memu-codex", "hook"]

    hook.install(argv)
    assert config.read_text() == 'notify = ["memu-codex", "hook"]\n'

    hook.remove("memu-codex")
    assert config.read_text() == ""


def test_codex_notify_hook_does_not_overwrite_existing_notify(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text('notify = ["existing-notifier"]\n')

    with pytest.raises(ValueError, match="already defines notify"):
        CodexNotifyHook(config).install(["memu-codex", "hook"])

    assert config.read_text() == 'notify = ["existing-notifier"]\n'


def test_diagnostic_window_logs_failure_and_holds(tmp_path, monkeypatch):
    import sys

    def fail(_argv):
        print("prepare failed", file=sys.stderr)
        return 2

    held = []
    monkeypatch.setattr("memu.hosts.codex.cli.main", fail)
    monkeypatch.setattr("builtins.input", lambda prompt: held.append(prompt))
    monkeypatch.setattr(
        sys, "argv", ["diagnostic", "--label", "desktop-codex", "--hold", "--", "hook-run", "--base-dir", str(tmp_path)]
    )
    assert notify_console.main() == 2
    log = (tmp_path / "hook.log").read_text()
    assert "prepare failed" in log
    assert "FINISHED desktop-codex exit=2" in log
    assert len(held) == 1


def test_headless_codex_disables_recursive_notify():
    from memu.hosts.codex.cli import HOOK

    assert "notify=[]" in HOOK.agent.argv
    assert "--dangerously-bypass-approvals-and-sandbox" in HOOK.agent.argv
    assert HOOK.launch_console is notify_console.launch
    assert HOOK.stream_output is notify_console.stream_agent


def test_hook_diagnostic_home_is_shared_by_worker(tmp_path, monkeypatch):
    import os

    from memu.hosts.codex.cli import main

    for key in ("HOME", "USERPROFILE", "CODEX_HOME", "MEMU_CONFIG_ENV"):
        monkeypatch.setenv(key, os.environ.get(key, ""))
    seen = []
    _patch_console_launcher(monkeypatch, lambda *args: seen.append((args, dict(os.environ))))
    assert main(["hook", "--diagnostic", "--diagnostic-home", str(tmp_path)]) == 0
    args, env = seen[0]
    assert env["HOME"] == str(tmp_path)
    assert env["CODEX_HOME"] == str(tmp_path / ".codex")
    assert env["MEMU_CONFIG_ENV"] == str(tmp_path / ".memu/config.env")
    assert args[1].base == tmp_path / ".memu/hosts/codex"


def test_diagnostic_workspace_lock_serializes_and_releases(tmp_path):
    import concurrent.futures
    import threading

    from memu.hosts.codex.notify_console import _workspace_lock

    entered = threading.Event()
    attempted = threading.Event()

    def second_worker():
        attempted.set()
        with _workspace_lock(tmp_path):
            entered.set()

    with concurrent.futures.ThreadPoolExecutor() as pool:
        with _workspace_lock(tmp_path):
            future = pool.submit(second_worker)
            assert attempted.wait(2)
            assert not entered.wait(0.2)
        future.result(timeout=3)
        assert entered.is_set()
