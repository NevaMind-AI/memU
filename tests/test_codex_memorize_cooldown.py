import concurrent.futures
import errno
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from memu.hosts import host_cli
from memu.hosts.bridging import Layout
from memu.hosts.codex import cli, hook_status, notify_console


def run_hook(base):
    return cli.main(["hook-run", "--base-dir", str(base)])


@pytest.fixture
def pipeline(monkeypatch):
    calls = []

    async def prepare(*_):
        calls.append("prepare")
        return 0

    async def commit(*_):
        calls.append("commit")
        return 0

    monkeypatch.setattr(host_cli, "_cmd_prepare", prepare)
    monkeypatch.setattr(host_cli, "_cmd_commit", commit)
    monkeypatch.setattr(host_cli.hooks, "pending_jobs", lambda _: True)
    monkeypatch.setattr(host_cli.hooks, "run_agent", lambda *a, **k: calls.append("evolve"))
    return calls


@pytest.mark.parametrize("elapsed,admitted", [(600, False), (1799, False), (1800, True), (3600, True)])
def test_start_time_boundary(tmp_path, monkeypatch, pipeline, capsys, elapsed, admitted):
    clock = [36000.0]  # 10:00
    monkeypatch.setattr(notify_console.time, "time", lambda: clock[0])
    assert run_hook(tmp_path) == 0
    assert pipeline == ["prepare", "evolve", "commit"]
    state = tmp_path / ".memorize_last_started.codex.json"
    assert json.loads(state.read_text()) == 36000
    pipeline.clear()
    clock[0] += elapsed
    assert run_hook(tmp_path) == 0
    assert bool(pipeline) is admitted
    assert json.loads(state.read_text()) == (clock[0] if admitted else 36000)
    assert ("status=cooldown" in capsys.readouterr().out) is not admitted


def test_activity_driven_and_skips_preserve_work(tmp_path, monkeypatch, pipeline):
    clock = [36000.0]
    monkeypatch.setattr(notify_console.time, "time", lambda: clock[0])
    assert run_hook(tmp_path) == 0
    layout = Layout.default("codex", tmp_path)
    files = [layout.session_manifest, layout.session_manifest_pending, layout.resource_log, layout.jobs / "1.txt"]
    for path in files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"pending input")
    pipeline.clear()
    clock[0] = 36600  # 10:10: skip
    assert run_hook(tmp_path) == 0
    clock[0] = 37800  # 10:30: no submission, no work
    assert pipeline == []
    assert all(path.read_bytes() == b"pending input" for path in files)
    clock[0] = 39600  # 11:00: next submission
    assert run_hook(tmp_path) == 0
    assert pipeline == ["prepare", "evolve", "commit"]


@pytest.mark.parametrize("outcome", ["exception", "nonzero", "no_input", "noop"])
def test_admitted_outcomes_consume_cooldown_and_release_lock(tmp_path, monkeypatch, pipeline, capsys, outcome):
    monkeypatch.setattr(notify_console.time, "time", lambda: 36000.0)
    if outcome == "exception":

        async def fail(*_):
            raise RuntimeError("synthetic pipeline failure")  # noqa: TRY003

        monkeypatch.setattr(host_cli, "_cmd_prepare", fail)
        monkeypatch.setattr(host_cli.events, "flush", lambda: None)
        monkeypatch.setattr(host_cli.events, "record_cli_error", lambda *a, **k: None)
    elif outcome == "nonzero":

        async def nonzero(*_):
            return 2

        monkeypatch.setattr(host_cli, "_cmd_prepare", nonzero)
    elif outcome == "no_input":
        monkeypatch.setattr(host_cli.hooks, "pending_jobs", lambda _: False)
    assert run_hook(tmp_path) == (1 if outcome == "exception" else 2 if outcome == "nonzero" else 0)
    with notify_console._workspace_lock(tmp_path) as acquired:
        assert acquired
    assert run_hook(tmp_path) == 0
    assert "status=cooldown" in capsys.readouterr().out


@pytest.mark.parametrize("contents", ["{broken", "null", "true", "NaN", "1e999", "-1", "40000", "\udcff"])
def test_invalid_state_or_clock_rollback_recovers(tmp_path, monkeypatch, pipeline, capsys, contents):
    state = tmp_path / ".memorize_last_started.codex.json"
    state.write_bytes(contents.encode("utf-8", errors="surrogateescape"))
    monkeypatch.setattr(notify_console.time, "time", lambda: 36000.0)
    assert run_hook(tmp_path) == 0
    assert pipeline == ["prepare", "evolve", "commit"]
    assert json.loads(state.read_text()) == 36000
    assert "warning:" in capsys.readouterr().out


def test_multiple_workers_skip_busy_even_after_cooldown(tmp_path):
    # Separate processes exercise the native OS lock and crash release.
    script = """
import sys,time
from pathlib import Path
from memu.hosts.bridging import Layout
from memu.hosts.codex.notify_console import memorize_run
with memorize_run(Layout.default('codex', sys.argv[1])) as admitted:
    assert admitted
    Path(sys.argv[1], 'entered').touch()
    time.sleep(60)
"""
    holder = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", script, str(tmp_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        deadline = time.monotonic() + 10
        while not (tmp_path / "entered").exists() and time.monotonic() < deadline:
            if holder.poll() is not None:
                pytest.fail(str(holder.communicate()))
            time.sleep(0.01)
        assert (tmp_path / "entered").exists()
        state = tmp_path / ".memorize_last_started.codex.json"
        original_start = state.read_bytes()
        state.write_text("0")  # Running longer than cooldown still holds the lock.
        script = """
import sys
from memu.hosts.codex import cli
from memu.hosts import host_cli
async def forbidden(*_):
    raise AssertionError('busy worker touched pipeline')
host_cli._cmd_prepare = forbidden
sys.exit(cli.main(['hook-run', '--base-dir', sys.argv[1]]))
"""
        with concurrent.futures.ThreadPoolExecutor() as pool:
            futures = [
                pool.submit(
                    subprocess.run,
                    [sys.executable, "-c", script, str(tmp_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                for _ in range(4)
            ]
            for future in futures:
                result = future.result(timeout=15)
                assert result.returncode == 0, result.stderr
                assert "status=busy" in result.stdout
        assert state.read_text() == "0"
        state.write_bytes(original_start)
    finally:
        holder.kill()  # Only this test's isolated synthetic process.
        holder.communicate(timeout=5)
    # A crash after admission keeps the recorded start, but never the OS lock.
    with notify_console._workspace_lock(tmp_path) as acquired:
        assert acquired
    with notify_console.memorize_run(Layout.default("codex", tmp_path)) as admitted:
        assert not admitted
    state.write_text("0")
    with notify_console.memorize_run(Layout.default("codex", tmp_path)) as admitted:
        assert admitted


def test_real_lock_error_is_not_busy(tmp_path, monkeypatch):
    module = __import__("msvcrt" if sys.platform == "win32" else "fcntl")

    def fail(*_):
        raise OSError(errno.EBADF, "synthetic lock failure")

    monkeypatch.setattr(module, "locking" if sys.platform == "win32" else "flock", fail)
    with pytest.raises(OSError, match="synthetic lock failure"), notify_console._workspace_lock(tmp_path):
        pass


@pytest.mark.parametrize(
    "status,code",
    [("worker_started", 2), ("started", 0), ("busy", 0), ("cooldown", 0), ("succeeded", 0), ("failed", 1)],
)
def test_worker_status_distinguishes_admission(tmp_path, capsys, status, code):
    folder = tmp_path / "log/hooks/memorize"
    folder.mkdir(parents=True)
    log = folder / "2026-01-02_00-00-02.000000-3.log"
    log.write_text(
        "=== WORKER codex pid=3 ===\n" + (f"=== MEMORIZE status={status} ===\n" if status != "worker_started" else "")
    )
    retrieve = tmp_path / "log/hooks/retrieve"
    retrieve.mkdir(parents=True)
    (retrieve / log.name).write_text('{"hook":"UserPromptSubmit","status":"empty_result"}\n')
    assert cli.main(["hook-status", "--since", "0", "--base-dir", str(tmp_path)]) == code
    assert json.loads(capsys.readouterr().out)["memorize"]["status"] == status


def test_title_then_user_content_waits_for_later_admitted_run(tmp_path, monkeypatch):
    from memu.hosts.bridging import pipeline
    from memu.hosts.codex.sessions import CodexTranscriptSource

    layout = Layout.default("codex", tmp_path / "workspace")
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    session = source_dir / "rollout-2026-10-20T10-00-00-01a15738-c76e-7661-a46c-6e3126d0d81a.jsonl"

    def append(text):
        with session.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"payload": {"type": "message", "role": "user", "content": text}}) + "\n")

    class Backend:
        async def list_all_recall_files(self, **_):
            return {"recall_files": [], "next_cursor": None}

        async def commit_results(self, **_):
            return {"status": "noop"}

    monkeypatch.setattr(pipeline, "build_agentic_memory_backend_from_env", Backend)
    monkeypatch.setattr(pipeline.templates, "resolve", lambda _name, embedded: embedded)
    clock = [36000.0]
    monkeypatch.setattr(notify_console.time, "time", lambda: clock[0])
    selected = []

    async def prepare(*_):
        await pipeline.prepare(CodexTranscriptSource(source_dir), layout, verify_command="unused")
        selected.append((layout.sessions / "1.jsonl").read_text())
        return 0

    async def commit(*_):
        await pipeline.commit(layout)
        return 0

    monkeypatch.setattr(host_cli, "_cmd_prepare", prepare)
    monkeypatch.setattr(host_cli, "_cmd_commit", commit)
    monkeypatch.setattr(host_cli.hooks, "run_agent", lambda *a, **k: None)
    append("Generate a concise task title")
    assert run_hook(layout.base) == 0
    cursor = layout.session_manifest.read_bytes()
    append("new user content after title")
    clock[0] += 1
    assert run_hook(layout.base) == 0
    assert layout.session_manifest.read_bytes() == cursor
    assert len(selected) == 1
    clock[0] += 1800
    assert run_hook(layout.base) == 0
    assert "new user content after title" in selected[1]
    assert "Generate a concise task title" not in selected[1]
    assert layout.session_manifest.read_bytes() != cursor
    assert not layout.session_manifest_pending.exists()
    assert not list(layout.jobs.glob("*.txt"))


@pytest.mark.parametrize("custom_base", [False, True])
def test_retrieve_ignores_memorize_lock_and_cooldown(tmp_path, monkeypatch, capsys, custom_base):
    import io

    from memu.hosts.codex import prompt_hook

    base = tmp_path / "custom host" if custom_base else tmp_path / ".memu/hosts/codex"
    base.mkdir(parents=True)
    (base / ".memorize_last_started.codex.json").write_text(json.dumps(time.time()))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    calls = []

    def retrieve(argv, **_):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, b'{"hits":[{"text":"synthetic memory"}]}', b"")

    monkeypatch.setattr(prompt_hook.subprocess, "run", retrieve)
    with notify_console._workspace_lock(base) as acquired:
        assert acquired
        for _ in range(2):
            monkeypatch.setattr(
                sys,
                "stdin",
                io.StringIO(json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": "synthetic query"})),
            )
            assert cli.main(["prompt-hook", *(["--base-dir", str(base)] if custom_base else [])]) == 0
            assert "synthetic memory" in capsys.readouterr().out
    assert len(calls) == 2
    assert hook_status.status(base, 0)["retrieve"]["status"] == "context_returned"


def test_default_callback_and_cli_share_host_base(tmp_path, monkeypatch, capsys):
    import asyncio
    import io

    from memu.hosts.codex import memorize_hook

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(
        os.path,
        "expanduser",
        lambda path: str(tmp_path / path[2:]) if path.startswith("~/") else str(tmp_path) if path == "~" else path,
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"hook_event_name":"UserPromptSubmit"}'))
    monkeypatch.delenv("MEMU_CODEX_MEMORIZE", raising=False)
    calls = []
    path = tmp_path / "worker.log"
    path.write_text("=== MEMORIZE status=started ===\n")

    def launch(*args):
        calls.append(args)
        return path

    monkeypatch.setattr(notify_console, "launch_background", launch)
    args = cli.build_parser().parse_args(["memorize-hook", "--agent", "unused"])
    assert asyncio.run(memorize_hook._cmd_memorize_hook(args)) == 0
    expected = str(tmp_path / ".memu/hosts/codex")
    assert str(calls[0][1].base) == expected
    assert cli.build_parser().parse_args(["hook-run"]).base_dir == "~/.memu/hosts/codex"
    assert cli.build_parser().parse_args(["hook-status", "--since", "0"]).base_dir == "~/.memu/hosts/codex"


@pytest.mark.parametrize("outcome", ["busy", "cooldown", "succeeded", "failed", "state_error"])
def test_logged_worker_admission_and_failure(tmp_path, monkeypatch, pipeline, outcome):
    import contextlib

    state = tmp_path / ".memorize_last_started.codex.json"
    if outcome == "cooldown":
        state.write_text(json.dumps(time.time()))
    elif outcome == "state_error":
        state.mkdir()  # A real I/O error must not be treated as corrupt content.
    elif outcome == "failed":

        async def fail(*_):
            return 2

        monkeypatch.setattr(host_cli, "_cmd_prepare", fail)
    monkeypatch.setattr(
        sys, "argv", ["worker", "--label", "test", "--background", "--", "hook-run", "--base-dir", str(tmp_path)]
    )
    monkeypatch.setattr(host_cli.events, "flush", lambda: None)
    monkeypatch.setattr(host_cli.events, "record_cli_error", lambda *a, **k: None)
    lock = notify_console._workspace_lock(tmp_path) if outcome == "busy" else contextlib.nullcontext()
    with lock:
        code = notify_console.main()
    assert code == (2 if outcome == "failed" else 1 if outcome == "state_error" else 0)
    actual = "failed" if outcome == "state_error" else outcome
    assert hook_status.status(tmp_path, 0)["memorize"]["status"] == actual
    log = next((tmp_path / "log/hooks/memorize").glob("*.log")).read_text()
    assert ("status=started" in log) is (outcome in {"succeeded", "failed"})
    if outcome in {"busy", "cooldown", "state_error"}:
        assert pipeline == []
    if outcome == "busy":
        assert not state.exists()
