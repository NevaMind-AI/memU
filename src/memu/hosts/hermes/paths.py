"""Hermes home paths, resolved with Hermes Agent's own precedence.

Hermes treats ``HERMES_HOME`` as the single source of truth for profiles,
containers, and native Windows installs.  Only an unset or whitespace-only
value falls back to the classic ``~/.hermes`` home.
"""

from __future__ import annotations

import os
from pathlib import Path


def hermes_home() -> Path:
    """Return the active Hermes home directory."""
    value = os.environ.get("HERMES_HOME", "").strip()
    return Path(value) if value else Path.home() / ".hermes"


def soul_path() -> Path:
    """Return the identity file loaded into every Hermes session."""
    return hermes_home() / "SOUL.md"


def state_db_path() -> Path:
    """Return Hermes's SQLite session store."""
    return hermes_home() / "state.db"
