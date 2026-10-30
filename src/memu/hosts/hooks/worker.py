"""Logged headless agent execution with process-tree cleanup on failure."""

from __future__ import annotations

import contextlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TextIO

from memu.hosts.bridging import Layout


def new_log_path(base: Path, hook: str = "memorize") -> Path:
    directory = base / "log" / "hooks" / hook
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{datetime.now():%Y-%m-%d_%H-%M-%S.%f}-{os.getpid()}.log"
    path.touch(exist_ok=False)
    return path


def _copy_output(
    stream: TextIO | None,
    log: TextIO | None,
    errors: list[Exception],
    on_output: Callable[[str], None] | None,
) -> None:
    try:
        if stream is not None:
            for line in stream:
                if on_output is not None:
                    on_output(line)
                if log is not None:
                    log.write(line)
                    log.flush()
                print(line, end="", flush=True)
    except Exception as exc:
        errors.append(exc)


def stream_agent(
    argv: list[str],
    layout: Layout,
    prompt: str,
    timeout: int,
    *,
    env: dict[str, str],
    on_output: Callable[[str], None] | None = None,
) -> None:
    """Stream full output once; kill the agent tree before releasing the caller."""
    # A file for stdin avoids a write/read pipe deadlock before the reader starts.
    name = getattr(sys.stdout, "name", None)
    log_context = (
        contextlib.nullcontext(None)
        if isinstance(name, str) and Path(name).parent == layout.base / "log" / "hooks" / "memorize"
        else new_log_path(layout.base).open("a", encoding="utf-8", buffering=1)
    )
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NO_WINDOW
    with tempfile.TemporaryFile() as source, log_context as log:
        source.write(prompt.encode("utf-8"))
        source.seek(0)
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
            reader = threading.Thread(target=_copy_output, args=(process.stdout, log, errors, on_output), daemon=True)
            deadline = time.monotonic() + timeout
            reader.start()
            try:
                print(f"=== AGENT pid={process.pid} parent={os.getpid()} argv={json.dumps(argv)} ===", flush=True)
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
