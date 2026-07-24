"""Register the bridging task with the host OS's scheduler.

Unix hosts schedule bridging by hand, following each host's ``BRIDGING_TASK.md``:
paste the pipeline prompt into a crontab, or a launchd plist. That path is stable
and unchanged. What was missing is Windows — Task Scheduler can't take a pasted
~1000-character quoted prompt (memU#539) and a bare scheduled process can't see a
desktop-only ``claude`` (memU#538) — so this package automates *only* the Windows
Task Scheduler registration, shared across every host adapter that sets
:attr:`~memu.hosts.host_cli.HostSpec.schedule_command`.

Nothing here touches the cron or launchd code paths.
"""

from __future__ import annotations

from memu.hosts.scheduling.windows import install, status, uninstall, verify

__all__ = ["install", "status", "uninstall", "verify"]
