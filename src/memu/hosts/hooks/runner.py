"""The detached half of hook mode: lock, headless agent, re-run bookkeeping.

``memu-<host> hook`` is what the host's hook runs, and it must return at once —
a session-end hook that blocked for the length of a bridging run would hold the
host hostage. So it only spawns ``memu-<host> hook-run`` detached and exits; the
pieces that run there live here. ``prepare`` and ``commit`` themselves are the
ordinary CLI handlers, called in-process by ``host_cli``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from memu.hosts.bridging import self_sessions
from memu.hosts.bridging.self_sessions import BRIDGING_RUN_ENV

if TYPE_CHECKING:
    from memu.hosts.bridging import Layout
    from memu.hosts.hooks.installers import HookInstaller

DEFAULT_AGENT_TIMEOUT_SECONDS = 60 * 60
"""One bridging pass is at most ten sessions; an hour is far past any real one."""

STALE_LOCK_SECONDS = DEFAULT_AGENT_TIMEOUT_SECONDS + 15 * 60
"""A lock older than the agent timeout plus slack belongs to a run that died."""

MAX_RERUNS = 3
"""How many extra passes one run makes for hooks that fired while it was busy."""

MAX_LOG_BYTES = 1_000_000
"""``hook.log`` is truncated past this when the next run is spawned."""


class HeadlessAgentError(RuntimeError):
    """The headless agent could not be started or exited non-zero."""

    @classmethod
    def not_found(cls, binary: str) -> HeadlessAgentError:
        return cls(f"`{binary}` is not on PATH; the hook run cannot start the agent")

    @classmethod
    def failed(cls, binary: str, returncode: int) -> HeadlessAgentError:
        return cls(f"`{binary}` exited {returncode}; the jobs stay on disk for the next run")

    @classmethod
    def timed_out(cls, binary: str, seconds: int) -> HeadlessAgentError:
        return cls(f"`{binary}` ran past {seconds}s and was stopped; the jobs stay on disk for the next run")


@dataclass(frozen=True)
class HeadlessAgent:
    """How to run this host's agent non-interactively over the job files.

    ``argv`` is the command, with ``{base}`` (the working tree, also the cwd) and
    ``{session_id}`` substituted. The prompt always goes on stdin, so no argv
    token has to survive a shell or a variadic flag swallowing it.
    """

    argv: tuple[str, ...]

    preset_session_id: bool = False
    """``argv`` takes a ``{session_id}`` we choose (``claude --session-id``), so the
    run's own transcript is claimed in :mod:`self_sessions` before it exists."""

    session_id_from_output: Callable[[str], str | None] | None = None
    """For agents that pick their own id: read it back from stdout after the run."""

    timeout_seconds: int = DEFAULT_AGENT_TIMEOUT_SECONDS


@dataclass(frozen=True)
class HookSpec:
    """Everything hook mode needs to know about one host."""

    agent: HeadlessAgent
    installer: HookInstaller
    min_interval_minutes: int = 0
    """Default cooldown between runs. Zero for a hook that fires once per session;
    a per-turn hook (Codex ``notify``) sets one so a long session is not re-mined
    after every reply."""


def jobs_prompt(layout: Layout) -> str:
    """The headless agent's whole brief: the job files, and nothing that needs a network."""
    jobs = layout.jobs
    return (
        "Process the memU self-evolve jobs. "
        f"List {jobs}/*.txt and process them in ascending numeric order (1.txt, then 2.txt, ...). "
        "The count changes every run - always glob and sort. "
        "For each job file: read it and follow its instructions to the letter. Each job is "
        "self-contained and already carries the concrete paths it needs. Finish one job before "
        "starting the next. Emitting no files for a job is a valid outcome; do not invent content. "
        "Where a job suggests a shell command to read or append to a file, your own file tools "
        "are fine too. Do not run any memU prepare or commit command - memU runs those itself "
        "after you finish. Finish with a one-line summary of what you wrote."
    )


def pending_jobs(layout: Layout) -> list[Path]:
    try:
        return sorted(layout.jobs.glob("*.txt"))
    except OSError:
        return []


def run_agent(agent: HeadlessAgent, layout: Layout, *, executable: str = "") -> None:
    """Run the agent over ``layout.jobs`` and claim its session so it is never mined.

    The agent's environment carries :data:`BRIDGING_RUN_ENV`: its own session-end
    hook fires too, and that is how the hook knows to stand down instead of
    recursing.
    """
    session_id = str(uuid4()) if agent.preset_session_id else ""
    if session_id:
        # Claimed before the transcript exists, so no later prepare can race it.
        self_sessions.remember(layout.self_sessions, session_id)
    argv = [token.replace("{base}", str(layout.base)).replace("{session_id}", session_id) for token in agent.argv]
    # Pinned by install-hook when it could resolve it: a hook inherits the host
    # app's PATH, and a desktop app's rarely matches the shell's.
    resolved = executable or shutil.which(argv[0])
    if not resolved:
        raise HeadlessAgentError.not_found(argv[0])
    try:
        proc = subprocess.run(  # noqa: S603 - argv is the host's declared agent command, not user input
            [resolved, *argv[1:]],
            input=jobs_prompt(layout),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=layout.base,
            env={**os.environ, BRIDGING_RUN_ENV: "1"},
            timeout=agent.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HeadlessAgentError.timed_out(argv[0], agent.timeout_seconds) from exc
    if agent.session_id_from_output is not None:
        found = agent.session_id_from_output(proc.stdout)
        if found:
            self_sessions.remember(layout.self_sessions, found)
        else:
            print(
                f"warning: could not read the {argv[0]} session id from its output; that session may be mined later",
                file=sys.stderr,
            )
    if proc.stderr.strip():
        print(proc.stderr.strip()[-4000:], file=sys.stderr)
    if proc.returncode != 0:
        raise HeadlessAgentError.failed(argv[0], proc.returncode)
    if agent.session_id_from_output is None and proc.stdout.strip():
        print(proc.stdout.strip()[-2000:])


def codex_thread_id(stdout: str) -> str | None:
    """The thread id ``codex exec --json`` announces in its ``thread.started`` event."""
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("type") == "thread.started":
            thread_id = event.get("thread_id")
            if isinstance(thread_id, str) and thread_id:
                return thread_id
    return None


@contextmanager
def run_lock(layout: Layout) -> Iterator[bool]:
    """Yield whether this process holds the hook-run lock; release it on exit.

    An exclusive-create file rather than ``flock``, because it behaves the same
    on Windows. A lock older than :data:`STALE_LOCK_SECONDS` is a run that died
    holding it, and is taken over.
    """
    path = layout.hook_lock
    path.parent.mkdir(parents=True, exist_ok=True)
    acquired = _try_create(path)
    if not acquired:
        try:
            stale = time.time() - path.stat().st_mtime > STALE_LOCK_SECONDS
        except OSError:
            stale = True
        if stale:
            path.unlink(missing_ok=True)
            acquired = _try_create(path)
    try:
        yield acquired
    finally:
        if acquired:
            path.unlink(missing_ok=True)


def _try_create(path: Path) -> bool:
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"pid": os.getpid(), "started_at": time.time()}))
    return True


def request_rerun(layout: Layout) -> None:
    """Tell the run in flight that another hook fired, so it makes one more pass."""
    layout.hook_rerun.parent.mkdir(parents=True, exist_ok=True)
    layout.hook_rerun.touch()


def take_rerun(layout: Layout) -> bool:
    try:
        layout.hook_rerun.unlink()
    except FileNotFoundError:
        return False
    return True


def cooling_down(layout: Layout, min_interval_minutes: int) -> bool:
    if min_interval_minutes <= 0:
        return False
    try:
        last = float(layout.hook_last_run.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return 0 <= time.time() - last < min_interval_minutes * 60


def stamp_run(layout: Layout) -> None:
    layout.hook_last_run.write_text(str(time.time()), encoding="utf-8")


def spawn_detached(argv: Sequence[str], layout: Layout) -> None:
    """Start ``argv`` in the background, output to ``hook.log``, and return at once."""
    log = layout.hook_log
    log.parent.mkdir(parents=True, exist_ok=True)
    try:
        if log.stat().st_size > MAX_LOG_BYTES:
            log.unlink()
    except OSError:
        pass
    env = {key: value for key, value in os.environ.items() if key != BRIDGING_RUN_ENV}
    windows = False
    creationflags = 0
    if sys.platform == "win32":
        windows = True
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    with log.open("a", encoding="utf-8") as out:
        out.write(f"\n=== hook run {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        out.flush()
        subprocess.Popen(  # noqa: S603 - our own interpreter and module
            list(argv),
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=subprocess.STDOUT,
            cwd=Path.home(),
            env=env,
            creationflags=creationflags,
            start_new_session=not windows,
        )
