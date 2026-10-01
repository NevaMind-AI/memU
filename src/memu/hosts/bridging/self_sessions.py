"""The bridging run's own session, remembered so ``prepare`` never mines it.

The record seam runs *as a session of the host agent*, and the host logs that
session in exactly the place memU discovers sessions from. Left alone that is a
loop: every run hands the next run fresh "new" content, so ``prepare`` can never
report zero, and the mining jobs chew through memU's own bookkeeping — the
newest transcripts on disk, so they sort to the top and take the ``max_jobs``
slots real conversations were waiting for (#606).

Claiming a session takes two facts, and they are known in different places:

    the launch  — "this is the scheduled run", but the session does not exist
                  yet, so its id cannot be known there
    inside it   — the host has put the session id in the environment
                  (:attr:`~memu.hosts.host_cli.HostSpec.session_id_env`), but a
                  process there cannot tell why it was started

``prepare`` is simply where the two meet: it runs *inside* the session, and it
inherits the launcher's environment. So running ``prepare`` is not part of the
condition — it is where the condition can be evaluated. Treating the command
itself as the signal is the bug this module was corrected for: people run
``prepare`` by hand, often meaning "remember this conversation now", and
claiming that session delivers the opposite, permanently.

Both signals live in the invocation rather than in the transcript, so the
identity is exact, and nothing can be forged later by a memory that happens to
quote the wrong text.

Hosts that expose no such variable are not served here. What to do for them is
open — see ADR 0015, which rejects matching a marker against transcript content
and records the alternatives — so this module deliberately offers no fallback.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, suppress
from pathlib import Path

MAX_REMEMBERED = 1000
"""How many ids to keep. One is added per run — hourly bridging takes six weeks
to fill this — and a session old enough to fall off the end is long gone from
the host's log too, so it cannot come back to be re-mined."""

BRIDGING_RUN_ENV = "MEMU_BRIDGING_RUN"
"""Set by the wrapper ``schedule install`` generates, so a run can tell that *it*
is the scheduled one."""

_LOCK_TIMEOUT_SECONDS = 5.0
_LOCK_STALE_SECONDS = 30.0
_LOCK_POLL_SECONDS = 0.01


class SelfSessionLockTimeout(TimeoutError):
    """The per-store self-session lock was not released in time."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"timed out waiting for self-session lock {path}")


def is_bridging_run(cwd: Path, base: Path, env: Mapping[str, str] | None = None) -> bool:
    """Whether this invocation is the scheduled bridging task, not a person.

    Running ``prepare`` is emphatically *not* the test. It is an ordinary command
    people run by hand — during development, or simply to say "remember this
    conversation now" — and treating that as a bridging run would exclude the very
    session the user asked to have mined, permanently and for every later run.

    What actually marks the scheduled task is how it was *launched*: the wrapper
    exports :data:`BRIDGING_RUN_ENV`. A working directory is not ownership — a
    person can run the host from memU's tree too — so ``cwd`` and ``base`` are
    retained only for call compatibility and are never used to claim a session.

    Fails open in the safe direction: unrecognised means "a person ran this", so
    nothing is recorded and nothing is skipped.
    """
    del cwd, base
    environ = os.environ if env is None else env
    return bool(environ.get(BRIDGING_RUN_ENV, "").strip())


@contextmanager
def _exclusive(path: Path) -> Iterator[None]:
    """Serialize read-modify-write updates to one self-session store.

    ``O_EXCL`` is atomic on the platforms memU supports and needs no dependency.
    The critical section is tiny; a stale marker is only reclaimed after a full
    process could not have been inside :func:`remember`.
    """
    lock = path.with_name(f"{path.name}.lock")
    deadline = time.monotonic() + _LOCK_TIMEOUT_SECONDS
    while True:
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            try:
                stale = time.time() - lock.stat().st_mtime >= _LOCK_STALE_SECONDS
            except FileNotFoundError:
                continue
            if stale:
                with suppress(FileNotFoundError):
                    lock.unlink()
                continue
            if time.monotonic() >= deadline:
                raise SelfSessionLockTimeout(lock) from None
            time.sleep(_LOCK_POLL_SECONDS)
        else:
            os.close(descriptor)
            break
    try:
        yield
    finally:
        with suppress(FileNotFoundError):
            lock.unlink()


def _write_atomic(path: Path, remembered: list[str]) -> None:
    """Replace the store in one step so readers never observe a partial write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(remembered, handle, indent=2)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load(path: Path) -> list[str]:
    """Session ids of previous bridging runs, oldest first.

    Fails open: an unreadable or malformed file yields no ids, so the worst case
    is the pre-#606 behaviour (self-sessions get mined) rather than a run that
    cannot start.
    """
    try:
        remembered = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [entry for entry in remembered if isinstance(entry, str)] if isinstance(remembered, list) else []


def remember(path: Path, session_id: str) -> list[str]:
    """Record this run's own session id, and return every id to skip.

    Idempotent: a re-run inside the same host session (a retried bridging task,
    or a bare ``prepare`` the user typed themselves) does not duplicate the id.
    Concurrent runs merge under an exclusive lock instead of overwriting one
    another's owner.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with _exclusive(path):
        remembered = load(path)
        if session_id not in remembered:
            remembered.append(session_id)
        remembered = remembered[-MAX_REMEMBERED:]
        _write_atomic(path, remembered)
    return remembered
