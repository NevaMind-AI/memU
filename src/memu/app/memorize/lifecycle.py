from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from memu.agentic_backend import AgenticMemoryBackend
from memu.app.memorize.input import MemorizeInput
from memu.app.memorize.materialize import (
    MaterializedConversation,
    _atomic_write_text,
    materialize_memorize_inputs,
)
from memu.hosts import templates  # noqa: F401 -- compatibility for template overrides
from memu.hosts.bridging.manifest import snapshot_tracked
from memu.run import RunWorkspace, commit_run, finish_run, mirror_run, prepare_run


@dataclass(frozen=True)
class MemorizeWorkspace(RunWorkspace):
    """Developer input paths over the shared run workspace."""

    @property
    def input(self) -> Path:
        return self.base / "input"

    @property
    def manifest(self) -> Path:
        return self.base / ".memorize_manifest.json"

    @property
    def active_run(self) -> Path:
        return self.base / ".memorize_run.json"


@dataclass(frozen=True, init=False)
class PreparedMemorizeRun:
    """The prepared inputs and jobs an external agent must process."""

    transcripts: list[MaterializedConversation]
    jobs: list[Path]

    def __init__(self, transcript: MaterializedConversation | list[MaterializedConversation], jobs: list[Path]) -> None:
        transcripts = [transcript] if isinstance(transcript, MaterializedConversation) else transcript
        if not transcripts:
            msg = "at least one transcript is required"
            raise ValueError(msg)
        object.__setattr__(self, "transcripts", transcripts)
        object.__setattr__(self, "jobs", jobs)

    @property
    def transcript(self) -> MaterializedConversation:
        """The first transcript, retained for single-session callers."""
        return self.transcripts[0]


def _numeric_path_key(path: Path) -> int:
    return int(path.stem)


async def prepare_memorize(
    memorize_input: list[MemorizeInput] | MemorizeInput,
    workspace: MemorizeWorkspace,
    backend: AgenticMemoryBackend,
    *,
    verify_command: str,
) -> PreparedMemorizeRun:
    """Prepare one batch of developer sessions for external self-evolve work."""

    memorize_inputs = [memorize_input] if isinstance(memorize_input, MemorizeInput) else memorize_input
    if not memorize_inputs:
        msg = "at least one memorize input is required"
        raise ValueError(msg)
    if workspace.active_run.exists():
        msg = "memorize workspace already has an active run"
        raise RuntimeError(msg)

    workspace.base.mkdir(parents=True, exist_ok=True)
    transcripts = materialize_memorize_inputs(memorize_inputs, workspace.input)
    await mirror_run(backend, workspace)
    snapshot_tracked(workspace.base, workspace.track_dirs, workspace.manifest)
    workspace.receipt.unlink(missing_ok=True)
    workspace.resources.unlink(missing_ok=True)
    prepare_run(workspace, len(memorize_inputs), verify_command=verify_command)

    _atomic_write_text(
        workspace.active_run,
        json.dumps({"schema_version": memorize_inputs[0].schema_version}, separators=(",", ":")) + "\n",
    )
    jobs = sorted(workspace.jobs.glob("*.txt"), key=_numeric_path_key)
    return PreparedMemorizeRun(transcript=transcripts, jobs=jobs)


async def commit_memorize(workspace: MemorizeWorkspace, backend: AgenticMemoryBackend) -> dict[str, Any]:
    """Commit one prepared developer run and clear its ephemeral artifacts."""

    if not workspace.active_run.is_file():
        msg = "memorize workspace has no active run"
        raise RuntimeError(msg)
    marker = json.loads(workspace.active_run.read_text(encoding="utf-8"))
    if marker.get("status") == "committed":
        msg = "memorize run already committed; do not resubmit; discard the stopped run"
        raise RuntimeError(msg)

    result = await commit_run(workspace, backend)

    # Persist the acknowledgement before cleanup can fail and leave a retryable run.
    # This does not cover an ambiguous backend failure or a crash before this write.
    marker["status"] = "committed"
    try:
        _atomic_write_text(workspace.active_run, json.dumps(marker, separators=(",", ":")) + "\n")
    except OSError as exc:
        msg = (
            f"memorize run committed, but could not persist its committed status at {workspace.base}: {exc}; "
            "do not resubmit; discard the stopped run"
        )
        raise RuntimeError(msg) from exc

    try:
        finish_run(workspace)
        workspace.resources.unlink(missing_ok=True)
        workspace.active_run.unlink()
    except OSError as exc:
        msg = (
            f"memorize run committed, but cleanup failed at {workspace.base}: {exc}; "
            "do not resubmit; discard the stopped run"
        )
        raise RuntimeError(msg) from exc
    return result
