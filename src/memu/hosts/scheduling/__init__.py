"""Register the bridging task with the host OS's scheduler.

One verb surface, two backends: Windows Task Scheduler (``windows.py``,
memU#538/#539) and cron on macOS/Linux (``unix.py``, memU#591). Both share the
same shape — the pipeline prompt lives in a file, a short generated wrapper
reads it, and the scheduler entry runs only the wrapper — because both
schedulers choke on a ~1.2 KB command line, just at different lengths (261
chars for ``schtasks /TR``, ~1 KB for a crontab line).

Shared across every host adapter that sets
:attr:`~memu.hosts.host_cli.HostSpec.schedule_command`; hosts with their own
scheduler (Codex, OpenClaw, WorkBuddy) never set it and never see these verbs.
launchd stays doc-driven, deliberately.
"""

from __future__ import annotations

import platform
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from memu.hosts.bridging import Layout
    from memu.hosts.host_cli import HostSpec

DEFAULT_INTERVAL_MINUTES = 60

# Lazy per-call imports keep module load light and let each backend's own
# platform gate stay the single source of "wrong OS" errors.


def install(spec: HostSpec, layout: Layout, *, interval_minutes: int = DEFAULT_INTERVAL_MINUTES) -> int:
    if platform.system() == "Windows":
        from memu.hosts.scheduling import windows as backend
    else:
        from memu.hosts.scheduling import unix as backend  # type: ignore[no-redef]
    return backend.install(spec, layout, interval_minutes=interval_minutes)


def uninstall(spec: HostSpec, layout: Layout) -> int:
    if platform.system() == "Windows":
        from memu.hosts.scheduling import windows as backend
    else:
        from memu.hosts.scheduling import unix as backend  # type: ignore[no-redef]
    return backend.uninstall(spec, layout)


def status(spec: HostSpec, layout: Layout) -> int:
    if platform.system() == "Windows":
        from memu.hosts.scheduling import windows as backend
    else:
        from memu.hosts.scheduling import unix as backend  # type: ignore[no-redef]
    return backend.status(spec, layout)


def verify(spec: HostSpec, layout: Layout) -> int:
    if platform.system() == "Windows":
        from memu.hosts.scheduling import windows as backend
    else:
        from memu.hosts.scheduling import unix as backend  # type: ignore[no-redef]
    return backend.verify(spec, layout)


__all__ = ["DEFAULT_INTERVAL_MINUTES", "install", "status", "uninstall", "verify"]
