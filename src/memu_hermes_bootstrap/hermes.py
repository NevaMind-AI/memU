"""Start ``memu-hermes`` without inheriting Hermes's Python environment.

Hermes launches shell tools from its own Python environment on Windows. Its
``PYTHONPATH`` can therefore put Hermes's dependencies ahead of the interpreter
that owns the ``memu-hermes`` console script. Keep this module independent of
``memu`` and third-party packages so it can restart the real CLI before either
is imported.

The isolation is Windows-only. On POSIX, delegate in-process so existing
macOS/Linux environment, signal, and process semantics stay unchanged.
"""

from __future__ import annotations

import os
import subprocess
import sys

ISOLATED_ENV_MARKER = "MEMU_HERMES_ISOLATED_ENV"
_HOST_PYTHON_ENV = ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV")


def _windows_main() -> int:
    env = os.environ.copy()
    removed = [name for name in _HOST_PYTHON_ENV if name in env]
    for name in removed:
        env.pop(name)
    if removed:
        # Pass names only: paths can contain user-specific or sensitive data.
        env[ISOLATED_ENV_MARKER] = ",".join(removed)

    command = [
        sys.executable,
        "-E",
        "-P",
        "-m",
        "memu.hosts.hermes.cli",
        *sys.argv[1:],
    ]
    try:
        return subprocess.call(command, env=env)  # noqa: S603
    except KeyboardInterrupt:
        return 130


def main() -> int:
    if os.name == "nt":
        return _windows_main()

    from memu.hosts.hermes.cli import main as hermes_main

    return hermes_main()
