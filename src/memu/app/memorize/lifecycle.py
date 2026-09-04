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
from memu.hosts import templates
from memu.hosts.bridging.instructions import MEMORY_JOB_TEMPLATE, SKILL_JOB_TEMPLATE, prepare_instruction_jobs
from memu.hosts.bridging.layout import TRACK_DIRS
from memu.hosts.bridging.manifest import diff_tracked, snapshot_tracked
from memu.hosts.bridging.recall_files import read_recall_file, write_recall_file
from memu.hosts.bridging.resources import RESOURCE_JOB_TEMPLATE, prepare_resource_job, read_resources


@dataclass(frozen=True)
class MemorizeWorkspace:
    """The developer-owned working tree for one evolving run at a time."""

    base: Path

    @property
    def input(self) -> Path:
        return self.base / "input"

    @property
    def jobs(self) -> Path:
        return self.base / "jobs"

    @property
    def memory(self) -> Path:
        return self.base / TRACK_DIRS["memory"]

    @property
    def skill(self) -> Path:
        return self.base / TRACK_DIRS["skill"]

    @property
    def manifest(self) -> Path:
        return self.base / ".memorize_manifest.json"

    @property
    def active_run(self) -> Path:
        return self.base / ".memorize_run.json"

    @property
    def resource_log(self) -> Path:
        return self.base / ".resource.tmp"

    @property
    def resources(self) -> Path:
        return self.base / "resources.md"

    @property
    def track_dirs(self) -> list[str]:
        return list(TRACK_DIRS.values())


@dataclass(frozen=True)
class PreparedMemorizeRun:
    """The prepared inputs and jobs an external agent must process."""

    transcripts: list[MaterializedConversation]
    jobs: list[Path]

    @property
    def transcript(self) -> MaterializedConversation:
        """The first transcript, retained for single-session callers."""
        return self.transcripts[0]


def _numeric_path_key(path: Path) -> int:
    return int(path.stem)


async def _mirror_recall_files(backend: AgenticMemoryBackend, workspace: MemorizeWorkspace) -> None:
    cursor: str | None = None
    while True:
        result = await backend.list_all_recall_files(cursor=cursor)
        for recall_file in result["recall_files"]:
            subdir = TRACK_DIRS.get(recall_file.get("track"))
            if subdir is not None:
                write_recall_file(workspace.base, subdir, recall_file)
        cursor = result.get("next_cursor")
        if not cursor:
            return


async def prepare_memorize(
    memorize_inputs: list[MemorizeInput] | MemorizeInput,
    workspace: MemorizeWorkspace,
    backend: AgenticMemoryBackend,
    *,
    verify_command: str,
) -> PreparedMemorizeRun:
    """Prepare one batch of developer sessions for external self-evolve work."""

    if isinstance(memorize_inputs, MemorizeInput):
        memorize_inputs = [memorize_inputs]
    if not memorize_inputs:
        msg = "at least one memorize input is required"
        raise ValueError(msg)
    if workspace.active_run.exists():
        msg = "memorize workspace already has an active run"
        raise RuntimeError(msg)

    workspace.base.mkdir(parents=True, exist_ok=True)
    transcripts = materialize_memorize_inputs(memorize_inputs, workspace.input)
    await _mirror_recall_files(backend, workspace)
    snapshot_tracked(workspace.base, workspace.track_dirs, workspace.manifest)

    workspace.resource_log.unlink(missing_ok=True)
    workspace.resources.unlink(missing_ok=True)
    num_sessions = len(memorize_inputs)
    prepare_instruction_jobs(
        job_dir=workspace.jobs,
        session_dir=workspace.input,
        memory_dir=workspace.memory,
        skill_dir=workspace.skill,
        resource_log=workspace.resource_log,
        num_sessions=num_sessions,
        memory_template=templates.resolve(templates.MEMORY_JOB, MEMORY_JOB_TEMPLATE),
        skill_template=templates.resolve(templates.SKILL_JOB, SKILL_JOB_TEMPLATE),
    )
    prepare_resource_job(
        job_dir=workspace.jobs,
        verify_command=verify_command,
        resource_file=workspace.resources,
        job_index=num_sessions * 2 + 1,
        template=templates.resolve(templates.RESOURCE_JOB, RESOURCE_JOB_TEMPLATE),
    )

    _atomic_write_text(
        workspace.active_run,
        json.dumps({"schema_version": memorize_inputs[0].schema_version}, separators=(",", ":")) + "\n",
    )
    jobs = sorted(workspace.jobs.glob("*.txt"), key=_numeric_path_key)
    return PreparedMemorizeRun(transcripts=transcripts, jobs=jobs)


async def commit_memorize(workspace: MemorizeWorkspace, backend: AgenticMemoryBackend) -> dict[str, Any]:
    """Commit one prepared developer run and clear its ephemeral artifacts."""

    if not workspace.active_run.is_file():
        msg = "memorize workspace has no active run"
        raise RuntimeError(msg)

    subdir_track = {subdir: track for track, subdir in TRACK_DIRS.items()}
    changed = diff_tracked(workspace.base, workspace.track_dirs, workspace.manifest)
    recall_files = [read_recall_file(path, subdir_track[path.relative_to(workspace.base).parts[0]]) for path in changed]
    resources = read_resources(workspace.resources)
    result = await backend.commit_results(recall_files=recall_files, resource=resources)

    snapshot_tracked(workspace.base, workspace.track_dirs, workspace.manifest)
    for stale in workspace.jobs.glob("*.txt"):
        stale.unlink()
    for stale in workspace.input.glob("*.jsonl"):
        stale.unlink()
    workspace.resource_log.unlink(missing_ok=True)
    workspace.resources.unlink(missing_ok=True)
    workspace.active_run.unlink()
    return result
