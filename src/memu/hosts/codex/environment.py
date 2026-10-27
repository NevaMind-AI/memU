"""Keep Submit subprocesses on the Codex home selected during installation."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def codex_environment(home: str | None) -> Iterator[None]:
    """Bind child processes to an explicit home, preserving legacy inherited behavior."""
    previous = os.environ.get("CODEX_HOME")
    if home is not None:
        os.environ["CODEX_HOME"] = str(Path(home).expanduser().resolve())
    try:
        yield
    finally:
        if home is not None:
            if previous is None:
                os.environ.pop("CODEX_HOME", None)
            else:
                os.environ["CODEX_HOME"] = previous
