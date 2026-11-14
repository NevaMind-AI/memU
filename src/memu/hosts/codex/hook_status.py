"""Read a background worker's startup snapshot without exposing its output."""

from __future__ import annotations

import math
import re
import time
from pathlib import Path
from typing import Any


def memorize_status(path: Path) -> dict[str, Any]:
    """Read one worker's admission/result snapshot without waiting for its pipeline."""
    entry: dict[str, Any] = {"status": "worker_started", "log": str(path)}
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if match := re.fullmatch(
                r"(?:\[[^\]\r\n]+\] )?=== MEMORIZE status=(started|busy|cooldown|succeeded|failed) ===\s*",
                line,
            ):
                entry["status"] = match[1]
            elif match := re.fullmatch(r"=== COOLDOWN until=(\d+(?:\.\d+)?) ===\s*", line):
                until = float(match[1])
                if math.isfinite(until):
                    entry["cooldown_until"] = until
    if entry["status"] == "cooldown" and "cooldown_until" in entry:
        entry["cooldown_remaining_minutes"] = math.ceil(max(0, entry["cooldown_until"] - time.time()) / 60)
    return entry
