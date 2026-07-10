"""Step 1 — slice raw agent sessions into numbered jsonl job inputs."""

import json
from pathlib import Path


def scan_sessions(raw_dir: Path) -> list[Path]:
    """All .jsonl session files under raw_dir (recursively), newest mtime first."""
    files = [p for p in raw_dir.rglob("*.jsonl") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def _read_lines(path: Path) -> list[str]:
    """Non-empty, stripped JSONL lines of a session file."""
    with path.open(encoding="utf-8") as fh:
        return [line for line in (raw.strip() for raw in fh) if line]


def _last_timestamp(lines: list[str]) -> str | None:
    for line in reversed(lines):
        try:
            ts = json.loads(line).get("timestamp")
        except json.JSONDecodeError:
            continue
        if ts:
            return ts
    return None


def _is_message(payload: dict) -> bool:
    return payload.get("type") == "message" and payload.get("role") in ("user", "assistant")


def _is_tool(payload: dict) -> bool:
    return payload.get("type") in ("function_call", "function_call_output")


def _split_lines(new_lines: list[str]) -> tuple[list[str], list[str]]:
    """Partition raw JSONL lines into (messages, messages+tool-calls)."""
    messages: list[str] = []
    full: list[str] = []
    for line in new_lines:
        try:
            payload = json.loads(line).get("payload", {})
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if _is_message(payload):
            messages.append(line)
            full.append(line)
        elif _is_tool(payload):
            full.append(line)
    return messages, full


def prepare_session_jobs(raw_dir: Path, out_dir: Path, manifest_path: Path, max_jobs: int) -> int:
    """Extract new session turns into numbered job files and update the manifest.

    Scans raw_dir newest-first, comparing each file's line count against the
    manifest cursor. The first already-seen file with no new lines ends the scan
    (older files cannot hold newer content). The latest max_jobs files with new
    lines are written oldest-first as <idx>.jsonl (user/assistant messages) and
    <idx>_full.jsonl (messages plus tool calls), with idx starting at 1.

    Returns the number of session files written (the highest idx emitted).
    """
    if not raw_dir.is_dir():
        return 0

    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

    # Collect sessions with new lines, newest-first, stopping at the first seen-but-unchanged file.
    pending: list[tuple[str, list[str], int]] = []
    for path in scan_sessions(raw_dir):
        key = path.relative_to(raw_dir).as_posix()
        prev = manifest.get(key)
        prev_count = prev["lines"] if prev else 0

        lines = _read_lines(path)
        if len(lines) > prev_count:
            pending.append((key, lines, prev_count))
        elif prev is not None:
            # Already recorded and no new lines: older files can't be newer either.
            break

    # Keep the latest max_jobs, then emit oldest-first so idx counts up with mtime.
    selected = pending[:max_jobs]
    selected.reverse()

    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.jsonl"):
        stale.unlink()

    for idx, (key, lines, prev_count) in enumerate(selected, start=1):
        messages, full = _split_lines(lines[prev_count:])

        (out_dir / f"{idx}.jsonl").write_text("\n".join(messages) + "\n", encoding="utf-8")
        (out_dir / f"{idx}_full.jsonl").write_text("\n".join(full) + "\n", encoding="utf-8")

        manifest[key] = {"lines": len(lines), "last_timestamp": _last_timestamp(lines)}

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return len(selected)
