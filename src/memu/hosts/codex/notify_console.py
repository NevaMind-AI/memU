"""Codex notify worker: background or visible execution with complete per-run logs."""

from __future__ import annotations

import argparse
import contextlib
import errno
import io
import json
import math
import os
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import TextIO, cast
from uuid import UUID

from memu.hosts.bridging import Layout, self_sessions


class _Tee(io.TextIOBase):
    def __init__(self, terminal: TextIO, log: TextIO) -> None:
        self.terminal = terminal
        self.log = log
        if isinstance(terminal, io.TextIOWrapper):
            terminal.reconfigure(errors="backslashreplace")

    @property
    def name(self) -> str:
        return str(self.log.name)

    def write(self, text: str) -> int:
        self.log.write(text)
        self.terminal.write(text)
        self.flush()
        return len(text)

    def flush(self) -> None:
        if not self.terminal.closed:
            self.terminal.flush()
        if not self.log.closed:
            self.log.flush()


def launch_background(argv: list[str], layout: Layout, label: str) -> None:
    """Run the logged worker independently of the notifying frontend's console."""
    layout.base.mkdir(parents=True, exist_ok=True)
    interpreter = str(Path(sys.executable).with_name("python.exe")) if sys.platform == "win32" else sys.executable
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NO_WINDOW
    subprocess.Popen(  # noqa: S603
        [interpreter, "-u", "-m", __name__, "--label", label, "--background", "--", *argv],
        cwd=layout.base,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=sys.platform != "win32",
        creationflags=flags,
    )


def launch(argv: list[str], layout: Layout, label: str, hold: bool) -> None:
    layout.base.mkdir(parents=True, exist_ok=True)
    interpreter = str(Path(sys.executable).with_name("python.exe")) if sys.platform == "win32" else sys.executable
    command = [interpreter, "-u", "-m", __name__, "--label", label]
    if hold:
        command.append("--hold")
    command += ["--", *argv]
    if sys.platform == "win32":
        subprocess.Popen(command, cwd=layout.base, creationflags=subprocess.CREATE_NEW_CONSOLE)  # noqa: S603
    elif sys.platform == "darwin":
        script = 'tell application "Terminal" to do script ' + json.dumps(shlex.join(command))
        subprocess.run(["osascript", "-e", script], check=True)  # noqa: S603, S607
    else:
        terminal = shutil.which("x-terminal-emulator") or shutil.which("xterm")
        if not terminal:
            raise RuntimeError("Diagnostic mode needs x-terminal-emulator or xterm")  # noqa: TRY003
        subprocess.Popen([terminal, "-e", *command], cwd=layout.base, start_new_session=True)  # noqa: S603


def _new_log_path(base: Path, hook: str = "memorize") -> Path:
    directory = base / "log" / "hooks" / hook
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{datetime.now():%Y-%m-%d_%H-%M-%S.%f}-{os.getpid()}.log"
    path.touch(exist_ok=False)
    return path


def _remember_thread(line: str, layout: Layout) -> None:
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return
    if not isinstance(event, dict) or event.get("type") != "thread.started":
        return
    thread_id = event.get("thread_id")
    if not isinstance(thread_id, str):
        return
    try:
        session_id = str(UUID(thread_id))
    except ValueError:
        return
    self_sessions.remember(layout.self_sessions, session_id)


def _copy_output(stream: TextIO | None, log: TextIO | None, errors: list[Exception], layout: Layout) -> None:
    try:
        if stream is not None:
            for line in stream:
                _remember_thread(line, layout)
                if log is not None:
                    log.write(line)
                    log.flush()
                print(line, end="", flush=True)
    except Exception as exc:
        errors.append(exc)


def stream_agent(argv: list[str], layout: Layout, prompt: str, timeout: int) -> None:
    # A file for stdin avoids a write/read pipe deadlock before the reader starts.
    # Match the sink across both module imports and execution as __main__.
    name = getattr(sys.stdout, "name", None)
    log_context = (
        contextlib.nullcontext(None)
        if isinstance(name, str) and Path(name).parent == layout.base / "log" / "hooks" / "memorize"
        else _new_log_path(layout.base).open("a", encoding="utf-8", buffering=1)
    )
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NO_WINDOW
    with tempfile.TemporaryFile() as source, log_context as log:
        source.write(prompt.encode("utf-8"))
        source.seek(0)
        env = os.environ.copy()
        env["MEMU_CODEX_MEMORIZE"] = "1"
        with subprocess.Popen(  # noqa: S603
            argv,
            env=env,
            stdin=source,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=layout.base,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=sys.platform != "win32",
            creationflags=flags,
        ) as process:
            errors: list[Exception] = []

            reader = threading.Thread(target=_copy_output, args=(process.stdout, log, errors, layout), daemon=True)
            deadline = time.monotonic() + timeout
            reader.start()
            try:
                print(f"=== AGENT pid={process.pid} parent={os.getpid()} argv={json.dumps(argv)} ===", flush=True)
                # A failed reader must stop the agent before its output pipe fills.
                reader.join(timeout=timeout)
                if errors:
                    raise errors[0]  # noqa: TRY301
                if reader.is_alive():
                    raise subprocess.TimeoutExpired(argv, timeout)  # noqa: TRY301
                code = process.wait(timeout=max(0, deadline - time.monotonic()))
            except BaseException:
                if sys.platform == "win32":
                    subprocess.run(  # noqa: S603
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],  # noqa: S607
                        check=False,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise
            finally:
                reader.join(timeout=5)
            if reader.is_alive():
                raise RuntimeError("Agent output pipe did not close")  # noqa: TRY003
            if code:
                raise RuntimeError(f"Agent exited {code}")  # noqa: TRY003


@contextlib.contextmanager
def _workspace_lock(base: Path) -> Iterator[bool]:
    """Try the whole-pass lock once; process exit also releases it."""
    with (base / ".diagnostic.lock").open("a+b") as lock:
        if lock.tell() == 0:
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        if sys.platform == "win32":
            import msvcrt

            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                yield False
                return
            try:
                yield True
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN):
                    raise
                yield False
                return
            try:
                yield True
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


COOLDOWN_SECONDS = 30 * 60


@contextlib.contextmanager
def memorize_run(layout: Layout) -> Iterator[bool]:
    """Coordinate admission for every Codex hook-run before touching pipeline state."""
    layout.base.mkdir(parents=True, exist_ok=True)
    with _workspace_lock(layout.base) as acquired:
        if not acquired:
            print("=== MEMORIZE status=busy ===", flush=True)
            yield False
            return
        state = layout.base / ".memorize_last_started.codex.json"
        now = time.time()
        try:
            previous = json.loads(state.read_text(encoding="utf-8"))
            if type(previous) not in (int, float) or not math.isfinite(previous) or previous < 0:
                raise ValueError("expected a finite nonnegative Unix timestamp")  # noqa: TRY003, TRY301
        except FileNotFoundError:
            previous = None
        except (ValueError, UnicodeError, OverflowError) as exc:
            print(f"warning: invalid memorize cooldown state at {state}: {exc}; resetting", flush=True)
            previous = None
        if previous is not None:
            elapsed = now - previous
            if elapsed < 0:
                print(f"warning: memorize clock moved backwards ({now} < {previous}); resetting", flush=True)
            elif elapsed < COOLDOWN_SECONDS:
                print("=== MEMORIZE status=cooldown ===", flush=True)
                yield False
                return
        # Persist before prepare: failures, no-input runs and crashes consume cooldown too.
        from memu.hosts.codex.prompt_hook_install import _atomic_write

        _atomic_write(state, json.dumps(now).encode("utf-8"))
        print("=== MEMORIZE status=started ===", flush=True)
        yield True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--hold", action="store_true")
    parser.add_argument("--background", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:]
    base = Path(command[command.index("--base-dir") + 1]).expanduser()
    log_path = _new_log_path(base)

    def report(message: str) -> None:
        message = f"[{time.strftime('%Y-%m-%d %H:%M:%S%z')}] {message}"
        with log_path.open("a", encoding="utf-8") as log:
            log.write(message + "\n")
        if not args.background:
            print(message, flush=True)

    code = 1
    report(f"=== WORKER {args.label} pid={os.getpid()} ===")
    report(f"worker parent={os.getppid()} source={__file__}")
    try:
        from memu.hosts.codex.cli import main as codex_main

        with (
            log_path.open("a", encoding="utf-8", buffering=1) as log,
            contextlib.redirect_stdout(log if args.background else cast(TextIO, _Tee(sys.stdout, log))),
            contextlib.redirect_stderr(log if args.background else cast(TextIO, _Tee(sys.stderr, log))),
        ):
            code = codex_main(command)
            if code:
                print("=== MEMORIZE status=failed ===", flush=True)
    except Exception:
        report("=== MEMORIZE status=failed ===")
        report(traceback.format_exc())
    finally:
        report(f"=== FINISHED {args.label} exit={code} ===")
        if args.hold:
            with contextlib.suppress(EOFError):
                input("Press Enter to close this diagnostic session...")
    return code


if __name__ == "__main__":
    sys.exit(main())
