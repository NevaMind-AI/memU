"""Codex notify worker: background or visible execution with complete hook.log output."""

from __future__ import annotations

import argparse
import contextlib
import errno
import io
import json
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
from pathlib import Path
from typing import TextIO, cast

from memu.hosts.bridging import Layout


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
    subprocess.Popen(  # noqa: S603
        [interpreter, "-u", "-m", __name__, "--label", label, "--background", "--", *argv],
        cwd=layout.base,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=sys.platform != "win32",
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
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


def _copy_output(stream: TextIO | None, log: TextIO | None, errors: list[Exception]) -> None:
    try:
        if stream is not None:
            for line in stream:
                if log is not None:
                    log.write(line)
                    log.flush()
                print(line, end="", flush=True)
    except Exception as exc:
        errors.append(exc)


def stream_agent(argv: list[str], layout: Layout, prompt: str, timeout: int) -> None:
    # A file for stdin avoids a write/read pipe deadlock before the reader starts.
    # Match the sink across both module imports and execution as __main__.
    log_context = (
        contextlib.nullcontext(None)
        if getattr(sys.stdout, "name", None) == str(layout.base / "hook.log")
        else (layout.base / "hook.log").open("a", encoding="utf-8")
    )
    with tempfile.TemporaryFile() as source, log_context as log:
        source.write(prompt.encode("utf-8"))
        source.seek(0)
        with subprocess.Popen(  # noqa: S603
            argv,
            stdin=source,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=layout.base,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=sys.platform != "win32",
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        ) as process:
            errors: list[Exception] = []

            reader = threading.Thread(target=_copy_output, args=(process.stdout, log, errors), daemon=True)
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
def _workspace_lock(base: Path) -> Iterator[None]:
    """Serialize notify workers; the OS releases the lock if a process exits."""
    with (base / ".diagnostic.lock").open("a+b") as lock:
        if lock.tell() == 0:
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        if sys.platform == "win32":
            import msvcrt

            while True:
                try:
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as exc:
                    if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                        raise
                    time.sleep(0.1)
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--hold", action="store_true")
    parser.add_argument("--background", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:]
    base = Path(command[command.index("--base-dir") + 1]).expanduser()
    base.mkdir(parents=True, exist_ok=True)

    def report(message: str) -> None:
        message = f"[{time.strftime('%Y-%m-%d %H:%M:%S%z')}] {message}"
        with (base / "hook.log").open("a", encoding="utf-8") as log:
            log.write(message + "\n")
        if not args.background:
            print(message, flush=True)

    code = 1
    report(f"=== START {args.label} pid={os.getpid()} ===")
    report(f"worker parent={os.getppid()} source={__file__}")
    try:
        from memu.hosts.codex.cli import main as codex_main

        report("Waiting for notify workspace...")
        with (
            _workspace_lock(base),
            (base / "hook.log").open("a", encoding="utf-8", buffering=1) as log,
            contextlib.redirect_stdout(log if args.background else cast(TextIO, _Tee(sys.stdout, log))),
            contextlib.redirect_stderr(log if args.background else cast(TextIO, _Tee(sys.stderr, log))),
        ):
            code = codex_main(command)
    except Exception:
        report(traceback.format_exc())
    finally:
        report(f"=== FINISHED {args.label} exit={code} ===")
        if args.hold:
            with contextlib.suppress(EOFError):
                input("Press Enter to close this diagnostic session...")
    return code


if __name__ == "__main__":
    sys.exit(main())
