"""The bridging run's own session, remembered so ``prepare`` never mines it.

The record seam runs *as a session of the host agent*, and the host logs that
session in exactly the place memU discovers sessions from. Left alone that is a
loop: every run hands the next run fresh "new" content, so ``prepare`` can never
report zero, and the mining jobs chew through memU's own bookkeeping — the
newest transcripts on disk, so they sort to the top and take the ``max_jobs``
slots real conversations were waiting for (#606).

The run identifies *itself*: ``prepare`` executes inside that very session, so
the host has already put the session id in the environment
(:attr:`~memu.hosts.host_cli.HostSpec.session_id_env`). That is an exact
identity rather than a guess about content — nothing is matched, so nothing can
be forged later by a memory that happens to quote the wrong text.

Hosts that expose no such variable are not served here; they need a fallback
keyed on the bridging prompt, which is deliberately not in this module.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path

MAX_REMEMBERED = 1000
"""How many ids to keep. One is added per run — hourly bridging takes six weeks
to fill this — and a session old enough to fall off the end is long gone from
the host's log too, so it cannot come back to be re-mined."""

BRIDGING_RUN_ENV = "MEMU_BRIDGING_RUN"
"""Set by the wrapper ``schedule install`` generates, so a run can tell that *it*
is the scheduled one."""


def is_bridging_run(cwd: Path, base: Path, env: Mapping[str, str] | None = None) -> bool:
    """Whether this invocation is the scheduled bridging task, not a person.

    Running ``prepare`` is emphatically *not* the test. It is an ordinary command
    people run by hand — during development, or simply to say "remember this
    conversation now" — and treating that as a bridging run would exclude the very
    session the user asked to have mined, permanently and for every later run.

    What actually marks the scheduled task is how it was *launched*: the wrapper
    exports :data:`BRIDGING_RUN_ENV`, and the task runs in memU's own working
    directory (``schedule`` passes ``-WorkingDirectory``; without it Task Scheduler
    would start in ``System32``). Either signal is enough — the directory keeps
    tasks registered before this existed working, and the variable survives an
    agent that changes directory before running the command.

    Fails open in the safe direction: unrecognised means "a person ran this", so
    nothing is recorded and nothing is skipped.
    """
    environ = os.environ if env is None else env
    if environ.get(BRIDGING_RUN_ENV, "").strip():
        return True
    return cwd == base


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
    """
    remembered = load(path)
    if session_id not in remembered:
        remembered.append(session_id)
    remembered = remembered[-MAX_REMEMBERED:]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(remembered, indent=2), encoding="utf-8")
    return remembered
