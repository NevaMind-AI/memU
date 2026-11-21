"""Real, isolated extraction processes must end with their owning request."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from contextlib import suppress
from pathlib import Path
from typing import Any

import pytest

from memu.hosts import query_extraction

_WORKER = """\
import pathlib, subprocess, sys, time
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
marker = pathlib.Path(sys.argv[1])
pending = marker.with_suffix('.tmp')
pending.write_text(str(child.pid))
pending.replace(marker)
time.sleep(30)
"""
_EXTRACTOR = f"""\
import json, os, pathlib, subprocess, sys, time
marker = pathlib.Path(sys.argv[1])
descendant = marker.with_suffix('.grandchild')
child = subprocess.Popen([sys.executable, '-c', {_WORKER!r}, str(descendant)],
    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
marker.write_text(json.dumps([os.getpid(), child.pid]))
while not descendant.is_file():
    time.sleep(0.01)
marker.write_text(json.dumps([os.getpid(), child.pid, int(descendant.read_text())]))
sys.stdout.buffer.write(b'owned-output')
sys.stdout.buffer.flush()
if sys.argv[2] == 'wait':
    time.sleep(30)
else:
    raise SystemExit(int(sys.argv[2]))
"""
_OWNER = """\
import os, pathlib, subprocess, sys
from memu.hosts.query_extraction import run_extraction
run_extraction([sys.executable, '-c', sys.argv[2], sys.argv[1], 'wait'], b'',
    pathlib.Path(sys.argv[3]), getattr(subprocess, 'CREATE_NO_WINDOW', 0),
    env=dict(os.environ), timeout=20)
"""


def _environment() -> dict[str, str]:
    # Subprocesses must exercise this checkout even when pytest uses an editable install elsewhere.
    return {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}


def _tree_pids(marker: Path) -> list[int]:
    try:
        pids = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pids = []
    descendant = marker.with_suffix(".grandchild")
    if descendant.is_file():
        pids.append(int(descendant.read_text(encoding="utf-8")))
    return list(dict.fromkeys(pids))


def _wait_for_tree(marker: Path) -> list[int]:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        pids = _tree_pids(marker)
        if len(pids) == 3:
            return pids
        time.sleep(0.02)
    pytest.fail("synthetic extractor did not publish its process tree")


def _running(pid: int) -> bool:
    if sys.platform == "win32":
        result = subprocess.run(  # noqa: S603
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],  # noqa: S607
            capture_output=True,
            check=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return f'"{pid}"'.encode() in result.stdout
    result = subprocess.run(  # noqa: S603
        ["ps", "-o", "stat=", "-p", str(pid)],  # noqa: S607
        capture_output=True,
        check=False,
        timeout=5,
    )
    state = result.stdout.strip()
    return bool(state and not state.startswith(b"Z"))


def _assert_tree_stopped(pids: list[int]) -> None:
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if not any(_running(pid) for pid in pids):
            return
        time.sleep(0.05)
    assert not [pid for pid in pids if _running(pid)], "extraction-owned process survived cleanup"


def _cleanup_tree(marker: Path) -> None:
    for pid in reversed(_tree_pids(marker)):
        if not _running(pid):
            continue
        if sys.platform == "win32":
            subprocess.run(  # noqa: S603
                ["taskkill", "/PID", str(pid), "/T", "/F"],  # noqa: S607
                capture_output=True,
                check=False,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            with suppress(ProcessLookupError):
                os.kill(pid, signal.SIGKILL)


@pytest.mark.parametrize("exit_code", [0, 3])
def test_completion_cleans_residual_descendants(tmp_path: Path, exit_code: int) -> None:
    marker = tmp_path / "tree.json"
    try:
        if exit_code:
            with pytest.raises(subprocess.CalledProcessError) as error:
                query_extraction.run_extraction(
                    [sys.executable, "-c", _EXTRACTOR, str(marker), str(exit_code)],
                    b"",
                    tmp_path,
                    getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    env=_environment(),
                )
            assert error.value.returncode == exit_code
        else:
            assert (
                query_extraction.run_extraction(
                    [sys.executable, "-c", _EXTRACTOR, str(marker), "0"],
                    b"",
                    tmp_path,
                    getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    env=_environment(),
                )
                == b"owned-output"
            )
        _assert_tree_stopped(_wait_for_tree(marker))
    finally:
        _cleanup_tree(marker)


@pytest.mark.parametrize(
    "termination",
    ["kill", pytest.param("terminate", marks=pytest.mark.skipif(sys.platform == "win32", reason="POSIX SIGTERM"))],
)
def test_owner_exit_cleans_tree_without_killing_unrelated_process(tmp_path: Path, termination: str) -> None:
    marker = tmp_path / "tree.json"
    unrelated = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    owner = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", _OWNER, str(marker), _EXTRACTOR, str(tmp_path)],
        env=_environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        pids = _wait_for_tree(marker)
        getattr(owner, termination)()
        owner.wait(timeout=5)
        _assert_tree_stopped(pids)
        assert unrelated.poll() is None
    finally:
        if owner.poll() is None:
            owner.kill()
        owner.wait(timeout=5)
        _cleanup_tree(marker)
        unrelated.kill()
        unrelated.wait(timeout=5)


def test_explicit_cancellation_is_idempotent_and_does_not_fall_back(tmp_path: Path) -> None:
    marker = tmp_path / "tree.json"
    cancellation = query_extraction.ExtractionCancellation()
    errors: list[BaseException] = []

    def extract() -> None:
        try:
            query_extraction.select_query(
                "x" * 600,
                {},
                lambda _: query_extraction.run_extraction(
                    [sys.executable, "-c", _EXTRACTOR, str(marker), "wait"],
                    b"",
                    tmp_path,
                    getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    env=_environment(),
                    timeout=10,
                    cancel=cancellation,
                ).decode(),
            )
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=extract, daemon=True)
    thread.start()
    try:
        pids = _wait_for_tree(marker)
        cancellation.cancel()
        cancellation.cancel()
        thread.join(timeout=5)
        assert not thread.is_alive()
        assert len(errors) == 1 and isinstance(errors[0], query_extraction.ExtractionCancelled)
        _assert_tree_stopped(pids)
    finally:
        cancellation.cancel()
        _cleanup_tree(marker)
        thread.join(timeout=5)


def test_cancelled_before_start_does_not_launch_extractor(tmp_path: Path) -> None:
    marker = tmp_path / "unexpected.txt"
    cancellation = query_extraction.ExtractionCancellation()
    cancellation.cancel()
    with pytest.raises(query_extraction.ExtractionCancelled):
        query_extraction.run_extraction(
            [sys.executable, "-c", "import pathlib,sys; pathlib.Path(sys.argv[1]).touch()", str(marker)],
            b"",
            tmp_path,
            getattr(subprocess, "CREATE_NO_WINDOW", 0),
            env=_environment(),
            cancel=cancellation,
        )
    assert not marker.exists()


def test_preserves_bytes_environment_and_working_directory(tmp_path: Path) -> None:
    source = "中文😀\x00input".encode()
    script = (
        "import os,pathlib,sys; "
        "pathlib.Path('environment.txt').write_text(os.environ['MEMU_TEST_EXTRACTION'],encoding='utf-8'); "
        "sys.stdout.buffer.write(sys.stdin.buffer.read())"
    )
    result = query_extraction.run_extraction(
        [sys.executable, "-c", script],
        source,
        tmp_path,
        getattr(subprocess, "CREATE_NO_WINDOW", 0),
        env={**_environment(), "MEMU_TEST_EXTRACTION": "synthetic-value"},
    )
    assert result == source
    assert (tmp_path / "environment.txt").read_text(encoding="utf-8") == "synthetic-value"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Job assignment gate")
def test_job_assignment_failure_falls_back_without_starting_extractor(tmp_path: Path, monkeypatch) -> None:
    from memu.hosts._extraction_job import WindowsExtractionJob

    marker = tmp_path / "unexpected.txt"
    attempts: list[int] = []
    assign = WindowsExtractionJob.assign

    def fail_once(self, process) -> None:
        if not attempts:
            attempts.append(process.pid)
            msg = "synthetic Job assignment failure"
            raise PermissionError(msg)
        assign(self, process)

    monkeypatch.setattr(WindowsExtractionJob, "assign", fail_once)
    trace: dict[str, Any] = {}
    query = query_extraction.select_query(
        "x" * 2500,
        trace,
        lambda _: query_extraction.run_extraction(
            [sys.executable, "-c", "import pathlib,sys; pathlib.Path(sys.argv[1]).touch()", str(marker)],
            b"",
            tmp_path,
            subprocess.CREATE_NO_WINDOW,
            env=_environment(),
        ).decode(),
    )
    assert query == "x" * 2000
    assert trace["extraction_status"] == "failed"
    assert len(attempts) == 1
    assert not marker.exists()
