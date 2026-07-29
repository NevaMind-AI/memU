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
from pathlib import Path

MAX_REMEMBERED = 1000
"""How many ids to keep. One is added per run — hourly bridging takes six weeks
to fill this — and a session old enough to fall off the end is long gone from
the host's log too, so it cannot come back to be re-mined."""


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
