"""Read-only Claude executable, authentication and local hook diagnostics."""

from __future__ import annotations

import subprocess

from memu.hosts.claude_code import cli_prepare, hook_install


def check() -> int:
    failed = False
    try:
        executable = cli_prepare.prepare()
        print(f"claude-cli ok ({executable})")
        if cli_prepare.auth_status(executable):
            print("authentication ok (CLI status; no model request)")
        else:
            print("authentication missing; run `claude auth login` or configure provider credentials")
            failed = True
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"claude-cli failed: {type(exc).__name__}; run install to diagnose or repair")
        failed = True
    try:
        issues = hook_install.problems()
        for issue in issues:
            print(issue)
        if not issues:
            print("prompt-hook / memorize-hook ok (local settings; runtime delivery unverified)")
        failed |= bool(issues)
    except (OSError, ValueError, TypeError) as exc:
        print(f"hooks failed: {exc}")
        failed = True
    if failed:
        print("hint: run `memu-claude-code install` to repair or update this integration.")
    return int(failed)
