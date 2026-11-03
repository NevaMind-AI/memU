"""Whole-cycle OS lock and startup cooldown for host memory workers."""

from __future__ import annotations

import contextlib
import errno
import json
import math
import sys
import time
from collections.abc import Iterator
from pathlib import Path

from memu.hosts.bridging import Layout
from memu.hosts.bridging.recall_files import _atomic_write_text


@contextlib.contextmanager
def workspace_lock(base: Path) -> Iterator[bool]:
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
def memorize_run(layout: Layout, *, cooldown_seconds: int = COOLDOWN_SECONDS) -> Iterator[bool]:
    """Coordinate admission before touching a host's pipeline state."""
    layout.base.mkdir(parents=True, exist_ok=True)
    with workspace_lock(layout.base) as acquired:
        if not acquired:
            print("=== MEMORIZE status=busy ===", flush=True)
            yield False
            return
        state = layout.base / f".memorize_last_started.{layout.host}.json"
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
            elif elapsed < cooldown_seconds:
                print(f"=== COOLDOWN until={previous + cooldown_seconds} ===", flush=True)
                print("=== MEMORIZE status=cooldown ===", flush=True)
                yield False
                return
        # Persist before prepare: failures, no-input runs and crashes consume cooldown too.
        _atomic_write_text(state, json.dumps(now))
        print("=== MEMORIZE status=started ===", flush=True)
        yield True
