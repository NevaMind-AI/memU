"""Start background memorization from a Codex UserPromptSubmit event."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from memu.hosts.bridging import Layout
from memu.hosts.codex import hook_status, notify_console

BACKGROUND_ENV = "MEMU_CODEX_MEMORIZE"


def _startup_snapshot(path: Path) -> dict[str, Any]:
    deadline = time.monotonic() + 0.5
    while True:
        snapshot = hook_status.memorize_status(path)
        if snapshot["status"] != "worker_started" or time.monotonic() >= deadline:
            return snapshot
        time.sleep(0.01)


def _context(snapshot: dict[str, Any]) -> dict[str, Any]:
    snapshot["observed_at"] = datetime.now(UTC).isoformat()
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": (
                "memU background memorization status snapshot (reference data). "
                "Use it when the user asks about memorization; do not proactively announce it. "
                "started means processing began and completion is unconfirmed; busy means this submission "
                "skipped because another run held the lock; worker_started means admission is unconfirmed. "
                "Cooldown minutes are rounded up at observed_at. This snapshot is not a live status; "
                "query hook-status for updated evidence.\n" + json.dumps(snapshot, ensure_ascii=False)
            ),
        }
    }


async def _cmd_memorize_hook(args: argparse.Namespace) -> int:
    output: dict[str, Any] = {}
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict) or event.get("hook_event_name") != "UserPromptSubmit":
            raise ValueError("expected a UserPromptSubmit object")  # noqa: TRY003, TRY301
        if os.environ.get(BACKGROUND_ENV) != "1":
            layout = Layout.default("codex", args.base_dir or "~/.memu/hosts/codex")
            path = notify_console.launch_background(
                ["hook-run", "--base-dir", str(layout.base), "--agent", args.agent, "--session-dir", args.session_dir],
                layout,
                "codex",
            )
            output = _context(_startup_snapshot(path))
    except (OSError, ValueError, TypeError) as exc:
        print(f"memU memorize hook failed: {exc}", file=sys.stderr)
        output = _context({"status": "failed", "error": str(exc)})
    print(json.dumps(output, ensure_ascii=False))
    return 0


def register(sub: Any) -> None:
    parser = sub.add_parser("memorize-hook", help="Start background memory processing on prompt submission")
    parser.add_argument("--base-dir", default=None)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--session-dir", default="~/.codex/sessions")
    parser.set_defaults(handler=_cmd_memorize_hook)
