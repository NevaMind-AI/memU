"""Read hook startup evidence without exposing retrieved content or worker output."""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any


def _since(value: str) -> float:
    try:
        timestamp = float(value)
    except ValueError:
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError as exc:
            raise argparse.ArgumentTypeError("Use Unix seconds or an ISO 8601 timestamp") from exc  # noqa: TRY003
    if not math.isfinite(timestamp):
        raise argparse.ArgumentTypeError("Timestamp must be finite")  # noqa: TRY003
    return timestamp


def _latest(directory: Path, since: float) -> Path | None:
    candidates = []
    for path in directory.glob("*.log"):
        try:
            started = datetime.strptime(path.name.rsplit("-", 1)[0], "%Y-%m-%d_%H-%M-%S.%f").timestamp()
        except ValueError:
            continue
        if started >= since:
            candidates.append((started, path))
    return max(candidates, default=(0.0, None), key=lambda entry: entry[0])[1]


def status(base: Path, since: float) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for kind in ("retrieve", "memorize"):
        path = _latest(base / "log" / "hooks" / kind, since)
        entry: dict[str, Any] = {"status": "not_observed", "log": str(path) if path else None}
        if path is not None:
            with path.open(encoding="utf-8", errors="replace") as stream:
                for line in stream:
                    if kind == "retrieve":
                        try:
                            trace = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(trace, dict) and trace.get("hook") == "UserPromptSubmit":
                            entry["status"] = trace.get("status", "started")
                            entry["exit_code"] = trace.get("retrieve_exit_code")
                    elif match := re.fullmatch(
                        r"(?:\[[^\]\r\n]+\] )?=== MEMORIZE status=(started|busy|cooldown|succeeded|failed) ===\s*",
                        line,
                    ):
                        entry["status"] = match[1]
                    elif re.fullmatch(r"(?:\[[^\]\r\n]+\] )?=== WORKER .+ pid=\d+ ===\s*", line):
                        entry["status"] = "worker_started"
        result[kind] = entry
    return result


async def _cmd(args: argparse.Namespace) -> int:
    result = status(Path(args.base_dir).expanduser(), args.since)
    print(json.dumps(result, ensure_ascii=False))
    retrieval = result["retrieve"]
    if retrieval["status"] == "failed" or result["memorize"]["status"] == "failed":
        return 1
    return (
        0
        if retrieval["status"] in {"context_returned", "empty_result"}
        and result["memorize"]["status"] in {"started", "succeeded", "busy", "cooldown"}
        else 2
    )


def register(sub: Any) -> None:
    parser = sub.add_parser("hook-status", help="Read retrieval and memorization startup evidence without waiting")
    parser.add_argument("--since", type=_since, required=True, help="Start of the check: Unix seconds or ISO 8601")
    parser.add_argument("--base-dir", default="~/.memu/hosts/codex")
    parser.set_defaults(handler=_cmd)
