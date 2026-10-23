"""Host ownership of private runs; the caller holds its stable whole-pass lock."""

from __future__ import annotations

import json
from pathlib import Path

from memu.hosts.bridging.layout import Layout
from memu.run import atomic_write_text, run_path


def cleanup_marker(layout: Layout) -> Path:
    return layout.state / f".run_cleanup.{layout.host}.json"


def cleanup_pending(layout: Layout) -> bool:
    marker = cleanup_marker(layout)
    return marker.exists() and json.loads(marker.read_text(encoding="utf-8"))["run_id"] == layout.base.name


def resolve(layout: Layout, run_id: str) -> Layout:
    if run_id == "legacy":
        return Layout(layout.state, layout.host, state_base=layout.state)
    try:
        path = run_path(layout.state / "runs", run_id)
    except FileNotFoundError:
        candidate = Layout(layout.state / "runs" / run_id, layout.host, state_base=layout.state)
        if not cleanup_pending(candidate):
            raise
        path = candidate.base
    return Layout(path, layout.host, state_base=layout.state)


def allocate(layout: Layout) -> Layout:
    if cleanup_marker(layout).exists():
        raise RuntimeError("a committed run needs cleanup; finish it with commit --run-id")  # noqa: TRY003
    pending = sorted((layout.state / "runs").glob("run-*"))
    if pending:
        raise RuntimeError(f"unfinished run {pending[0].name}; resume, commit or discard it before preparing")  # noqa: TRY003
    if layout.session_manifest_pending.exists() or any(layout.jobs.glob("*.txt")):
        raise RuntimeError("legacy workspace has unfinished work; commit --run-id legacy before preparing")  # noqa: TRY003
    result = Layout(run_path(layout.state / "runs"), layout.host, state_base=layout.state)
    set_phase(result, "preparing")
    atomic_write_text(
        result.base / ".cursor_before.json",
        layout.session_manifest.read_text(encoding="utf-8") if layout.session_manifest.exists() else "{}\n",
    )
    return result


def set_phase(layout: Layout, phase: str) -> None:
    atomic_write_text(
        layout.base / ".run.json",
        json.dumps({"host": layout.host, "run_id": layout.base.name, "phase": phase}) + "\n",
    )


def phase(layout: Layout) -> str:
    data = json.loads((layout.base / ".run.json").read_text(encoding="utf-8"))
    if data["host"] != layout.host:
        raise ValueError("run belongs to a different host")  # noqa: TRY003
    return str(data["phase"])
