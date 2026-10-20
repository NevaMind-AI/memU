from __future__ import annotations

import json
import subprocess

import pytest

from memu.hosts.bridging import Layout
from memu.hosts.codex import notify_console
from memu.hosts.hooks import CodexNotifyHook, HeadlessAgent, run_agent


def _patch_console_launcher(monkeypatch, launch):
    from dataclasses import replace

    from memu.hosts.codex import cli

    monkeypatch.setattr(cli, "SPEC", replace(cli.SPEC, hook=replace(cli.HOOK, launch_console=launch)))


def test_console_agent_output_is_live(tmp_path, capsys):
    import concurrent.futures
    import sys
    import time

    layout = Layout.default("codex", tmp_path)
    thread_id = "01a15739-1522-7003-b1d4-c13585d5ac95"
    script = (
        "import sys,time,pathlib; sys.stdin.read(); "
        f"print({json.dumps({'type': 'thread.started', 'thread_id': thread_id})!r},flush=True); "
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
                logs = list((tmp_path / "log").glob("*.log"))
                if logs and "agent stderr" in logs[0].read_text():
                    break
                time.sleep(0.01)
            assert len(logs) == 1
            log = logs[0]
            assert "agent stdout" in log.read_text()
            assert "agent stderr" in log.read_text()
            assert json.loads(layout.self_sessions.read_text()) == [thread_id]
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
def test_console_agent_failure_and_timeout(tmp_path, script, timeout, error):
    import sys

    with pytest.raises(error):
        run_agent(
            HeadlessAgent((sys.executable, "-c", script), timeout),
            Layout.default("codex", tmp_path),
            stream_output=notify_console.stream_agent,
        )
    assert next((tmp_path / "log").glob("*.log")).read_text()


@pytest.mark.parametrize("ending", ["pass", "sys.exit(7)", "time.sleep(30)"])
def test_agent_thread_is_excluded_from_next_prepare(tmp_path, ending):
    import contextlib
    import sys

    from memu.hosts.bridging import self_sessions
    from memu.hosts.bridging.transcripts import prepare_transcripts
    from memu.hosts.codex.sessions import CodexTranscriptSource

    layout = Layout.default("codex", tmp_path)
    thread_id = "01a15739-1522-7003-b1d4-c13585d5ac95"
    user_id = "01a15738-c76e-7661-a46c-6e3126d0d81a"
    event = json.dumps({"type": "thread.started", "thread_id": thread_id})
    script = (
        "import sys,time; "
        "print('startup warning',flush=True); print('[]',flush=True); "
        "print('{broken',flush=True); "
        'print(\'{"type":"thread.started","thread_id":""}\',flush=True); '
        f"print({event!r},flush=True); print({event!r},flush=True); {ending}"
    )
    error = subprocess.TimeoutExpired if ending.startswith("time.sleep") else RuntimeError
    expected = contextlib.nullcontext() if ending == "pass" else pytest.raises(error)
    with expected:
        notify_console.stream_agent([sys.executable, "-c", script], layout, "test", 1)
    assert self_sessions.load(layout.self_sessions) == [thread_id]
    assert event in next((tmp_path / "log").glob("*.log")).read_text()

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    for session_id, text in [(user_id, "new user content"), (thread_id, "background bookkeeping")]:
        path = source_dir / f"rollout-2026-10-20T10-52-01-{session_id}.jsonl"
        path.write_text(json.dumps({"payload": {"type": "message", "role": "user", "content": text}}) + "\n")
    source = CodexTranscriptSource(source_dir)
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
    assert "new user content" in (layout.sessions / "1.jsonl").read_text()
    assert "background bookkeeping" not in (layout.sessions / "1_full.jsonl").read_text()
    pending = json.loads(layout.session_manifest_pending.read_text())
    assert len(pending) == 1 and user_id in next(iter(pending))


def test_hook_passes_console_options(tmp_path, monkeypatch):
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
            "--console",
            "--hold",
            "--label",
            "desktop-codex",
            '{"turn-id":"test"}',
        ])
        == 0
    )
    argv, _layout, label, hold = calls[0]
    assert "--console" in argv
    assert argv[argv.index("--session-dir") + 1] == "~/sessions"
    assert label == "desktop-codex" and hold


@pytest.mark.parametrize("platform", ["win32", "darwin", "linux"])
def test_console_launch_platform(tmp_path, monkeypatch, platform):
    calls = []
    monkeypatch.setattr(notify_console.sys, "platform", platform)
    monkeypatch.setattr(
        notify_console.sys, "executable", "/venv/pythonw.exe" if platform == "win32" else "/venv/python"
    )
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
    if platform == "win32":
        assert args[0][0].endswith("python.exe")


@pytest.mark.parametrize("platform", ["win32", "darwin", "linux"])
def test_background_launch_has_no_console(tmp_path, monkeypatch, platform):
    calls = []
    monkeypatch.setattr(notify_console.sys, "platform", platform)
    monkeypatch.setattr(notify_console.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    monkeypatch.setattr(notify_console.subprocess, "Popen", lambda *a, **k: calls.append((a, k)))
    notify_console.launch_background(
        ["hook-run", "--base-dir", str(tmp_path)], Layout.default("codex", tmp_path), "codex"
    )
    args, kwargs = calls[0]
    assert "memu.hosts.codex.notify_console" in args[0]
    assert "--hold" not in args[0] and "--background" in args[0]
    assert kwargs["creationflags"] == (0x08000000 if platform == "win32" else 0)
    assert kwargs["start_new_session"] == (platform != "win32")
    assert all(kwargs[stream] == subprocess.DEVNULL for stream in ("stdin", "stdout", "stderr"))


def test_background_hook_uses_packaged_worker(tmp_path, monkeypatch):
    from dataclasses import replace

    from memu.hosts.codex import cli

    calls = []
    hook = replace(cli.HOOK, launch_background=lambda *args: calls.append(args))
    monkeypatch.setattr(cli, "SPEC", replace(cli.SPEC, hook=hook))
    assert cli.main(["hook", "--base-dir", str(tmp_path)]) == 0
    argv, layout, label = calls[0]
    assert argv[0] == "hook-run" and "--console" not in argv
    assert layout.base == tmp_path and label == "codex"


@pytest.mark.parametrize("platform", ["win32", "darwin", "linux"])
def test_agent_launch_platform_flags(tmp_path, monkeypatch, platform):
    import io

    class Process:
        pid = 123
        stdout = io.StringIO("agent output\n")

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def wait(self, timeout=None):
            return 0

    calls = []
    monkeypatch.setattr(notify_console.sys, "platform", platform)
    monkeypatch.setattr(notify_console.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)

    def popen(*args, **kwargs):
        calls.append((args, kwargs))
        return Process()

    monkeypatch.setattr(notify_console.subprocess, "Popen", popen)
    notify_console.stream_agent(["codex", "exec"], Layout.default("codex", tmp_path), "test", 10)
    args, kwargs = calls[0]
    assert args[0] == ["codex", "exec"]
    assert kwargs["creationflags"] == (0x08000000 if platform == "win32" else 0)
    assert kwargs["start_new_session"] == (platform != "win32")


def test_codex_notify_hook_installs_and_removes_its_own_command(tmp_path):
    config = tmp_path / "config.toml"
    hook = CodexNotifyHook(config)
    argv = ["memu-codex", "hook"]

    hook.install(argv)
    assert config.read_text() == 'notify = ["memu-codex", "hook"]\n'

    hook.remove("memu-codex")
    assert config.read_text() == ""


@pytest.mark.parametrize("platform", ["win32", "darwin", "linux"])
def test_install_hook_uses_windowless_package_entry_only_on_windows(tmp_path, monkeypatch, platform):
    from dataclasses import replace

    from memu.hosts import host_cli
    from memu.hosts.codex import cli

    config = tmp_path / "config.toml"
    hook = replace(cli.HOOK, installer=CodexNotifyHook(config))
    monkeypatch.setattr(cli, "SPEC", replace(cli.SPEC, hook=hook))
    monkeypatch.setattr(host_cli.sys, "platform", platform)
    monkeypatch.setattr(host_cli.shutil, "which", lambda binary: binary)
    assert cli.main(["install-hook"]) == 0
    command = hook.installer._notify()
    assert command is not None
    if platform == "win32":
        assert command[:2] == ["memu-codex-notify", "hook"]
    else:
        assert command[:2] == ["memu-codex", "hook"]
    hook.installer.remove("memu-codex")
    assert hook.installer._notify() is None


def test_install_hook_missing_entry_leaves_config_untouched(tmp_path, monkeypatch):
    from dataclasses import replace

    from memu.hosts import host_cli
    from memu.hosts.codex import cli

    config = tmp_path / "config.toml"
    config.write_text('model = "test"\n')
    hook = replace(cli.HOOK, installer=CodexNotifyHook(config))
    monkeypatch.setattr(cli, "SPEC", replace(cli.SPEC, hook=hook))
    monkeypatch.setattr(host_cli.shutil, "which", lambda _: None)
    assert cli.main(["install-hook"]) == 1
    assert config.read_text() == 'model = "test"\n'


def test_uninstall_leaves_unrelated_pythonw_notify(tmp_path):
    config = tmp_path / "config.toml"
    hook = CodexNotifyHook(config)
    command = ["pythonw.exe", "-m", "other.cli", "hook"]
    hook.install(command)
    hook.remove("memu-codex")
    assert hook._notify() == command


def test_codex_notify_hook_does_not_overwrite_existing_notify(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text('notify = ["existing-notifier"]\n')

    with pytest.raises(ValueError, match="already defines notify"):
        CodexNotifyHook(config).install(["memu-codex", "hook"])

    assert config.read_text() == 'notify = ["existing-notifier"]\n'


def test_background_worker_streams_full_output_to_log(tmp_path, monkeypatch, capsys):
    import sys

    def run(_argv):
        run_agent(
            HeadlessAgent((sys.executable, "-c", "import sys; print('x'*5000); print('stderr',file=sys.stderr)")),
            Layout.default("codex", tmp_path),
            stream_output=notify_console.stream_agent,
        )
        return 0

    monkeypatch.setattr("memu.hosts.codex.cli.main", run)
    monkeypatch.setattr(
        sys, "argv", ["worker", "--label", "test", "--background", "--", "hook-run", "--base-dir", str(tmp_path)]
    )
    assert notify_console.main() == 0
    assert capsys.readouterr() == ("", "")
    logs = list((tmp_path / "log").glob("*.log"))
    assert len(logs) == 1
    log = logs[0].read_text()
    assert "x" * 5000 in log and log.splitlines().count("stderr") == 1
    assert "FINISHED test exit=0" in log


@pytest.mark.parametrize("background", [True, False])
def test_worker_logs_unicode_once_under_module_execution(tmp_path, background):
    import re
    import sys

    message = "中文日志 \ue6c6 😀"
    script = """
import io, runpy, sys
from memu.hosts.codex import cli, notify_console
from memu.hosts.bridging import Layout
sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="gbk", errors="strict")
sys.stderr = io.TextIOWrapper(io.BytesIO(), encoding="gbk", errors="strict")
agent, base, message, *flags = sys.argv[1:]
def run(argv, agent=agent, base=base, message=message):
    notify_console.stream_agent([sys.executable, "-c", agent], Layout.default("codex", base), "test", 10)
    print("worker final report: " + message)
    return 0
cli.main = run
sys.argv = ["worker", "--label", "unicode", *flags, "--", "hook-run", "--base-dir", base]
runpy.run_module("memu.hosts.codex.notify_console", run_name="__main__")
"""
    historical = tmp_path / "hook.log"
    historical.write_bytes(b"historical log\n")
    previous_logs = set((tmp_path / "log").glob("*.log"))
    for number in range(2):
        run_message = f"{message} run-{number}"
        agent = (
            f"import sys; sys.stdout.buffer.write({(run_message + chr(10)).encode()!r}); "
            f"sys.stderr.buffer.write({('stderr: ' + run_message + chr(10)).encode()!r})"
        )
        result = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-c",
                script,
                agent,
                str(tmp_path),
                run_message,
                *(["--background"] if background else []),
            ],
            capture_output=True,
            timeout=20,
            check=False,
        )
        assert result.returncode == 0, result.stderr.decode(errors="replace")
        logs = set((tmp_path / "log").glob("*.log"))
        new_logs = logs - previous_logs
        assert len(new_logs) == 1
        path = new_logs.pop()
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.\d{6}-\d+\.log", path.name)
        log = path.read_text(encoding="utf-8")
        assert log.splitlines().count(run_message) == 1
        assert log.splitlines().count("stderr: " + run_message) == 1
        assert "worker final report: " + run_message in log
        assert "FINISHED unicode exit=0" in log
        assert f"run-{1 - number}" not in log
        previous_logs = logs
    assert len(previous_logs) == 2
    assert historical.read_bytes() == b"historical log\n"


def test_agent_output_failure_stops_waiting_and_cleans_up(tmp_path, monkeypatch):
    import io
    import sys
    import time

    class BrokenTerminal(io.StringIO):
        def write(self, text):
            if text.startswith("agent output"):
                raise OSError("output sink failed")  # noqa: TRY003
            return super().write(text)

    processes = []
    popen = subprocess.Popen

    def capture_process(*args, **kwargs):
        process = popen(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(notify_console.subprocess, "Popen", capture_process)
    monkeypatch.setattr(sys, "stdout", BrokenTerminal())
    started = time.monotonic()
    with pytest.raises(OSError, match="output sink failed"):
        notify_console.stream_agent(
            [
                sys.executable,
                "-c",
                "import time; print('agent output',flush=True); print('x'*1000000,flush=True); time.sleep(30)",
            ],
            Layout.default("codex", tmp_path),
            "test",
            5,
        )
    assert time.monotonic() - started < 4
    assert processes[0].poll() is not None


def test_console_window_logs_failure_and_holds(tmp_path, monkeypatch):
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
    log = next((tmp_path / "log").glob("*.log")).read_text()
    assert "prepare failed" in log
    assert "FINISHED desktop-codex exit=2" in log
    assert len(held) == 1


def test_headless_codex_disables_recursive_notify():
    from memu.hosts.codex.cli import HOOK

    assert "notify=[]" in HOOK.agent.argv
    assert "--dangerously-bypass-approvals-and-sandbox" in HOOK.agent.argv
    assert HOOK.launch_background is notify_console.launch_background
    assert HOOK.launch_console is notify_console.launch
    assert HOOK.stream_output is notify_console.stream_agent


def test_hook_preserves_home_and_backend_config(tmp_path, monkeypatch):
    import os

    from memu.hosts.codex.cli import main

    expected = {key: str(tmp_path / key) for key in ("HOME", "USERPROFILE", "CODEX_HOME", "MEMU_CONFIG_ENV")}
    for key, value in expected.items():
        monkeypatch.setenv(key, value)
    seen = []
    _patch_console_launcher(monkeypatch, lambda *args: seen.append(dict(os.environ)))
    assert main(["hook", "--console", "--base-dir", str(tmp_path)]) == 0
    assert {key: seen[0][key] for key in expected} == expected


def test_console_workspace_lock_serializes_and_releases(tmp_path):
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
