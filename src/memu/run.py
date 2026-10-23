"""Shared on-disk runs for developer input and host transcript adapters.

Input projection, host cursors and execution admission belong to the callers.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from memu.agentic_backend import AgenticMemoryBackend


def atomic_write_text(path: Path, content: str) -> None:
    fd, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temporary_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary_name)
        raise


TRACK_DIRS: dict[str, str] = {"memory": "memory", "skill": "skill"}


@dataclass(frozen=True)
class RunWorkspace:
    base: Path

    @property
    def input(self) -> Path:
        return self.base / "sessions"

    @property
    def jobs(self) -> Path:
        return self.base / "jobs"

    @property
    def memory(self) -> Path:
        return self.base / "memory"

    @property
    def skill(self) -> Path:
        return self.base / "skill"

    @property
    def manifest(self) -> Path:
        return self.base / ".memory_manifest.json"

    @property
    def resource_log(self) -> Path:
        return self.base / ".resource.tmp"

    @property
    def resources(self) -> Path:
        return self.base / "resources.md"

    @property
    def receipt(self) -> Path:
        return self.base / ".commit_result.json"

    @property
    def track_dirs(self) -> list[str]:
        return list(TRACK_DIRS.values())


def run_path(root: Path, run_id: str | None = None) -> Path:
    """Allocate or resolve a direct child of a caller-owned runs root."""
    root = root.expanduser().resolve()
    if run_id is None:
        root.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix="run-", dir=root))
    if not re.fullmatch(r"run-[a-z0-9_]{1,64}", run_id):
        raise ValueError("invalid memorize run id")  # noqa: TRY003
    path = root / run_id
    if path.is_symlink() or path.resolve() != path:
        raise ValueError("memorize run must be a directory directly below the runs root")  # noqa: TRY003
    if not path.is_dir():
        raise FileNotFoundError(f"no such memorize run: {run_id}")  # noqa: TRY003
    return path


def discard_run(workspace: RunWorkspace) -> None:
    """Remove a stopped run; the caller coordinates its executor and ownership."""
    shutil.rmtree(workspace.base)


async def mirror_run(
    backend: AgenticMemoryBackend, workspace: RunWorkspace, *, progress: Callable[[int], None] | None = None
) -> int:
    from memu.hosts.bridging.recall_files import write_recall_file

    listed = 0
    cursor: str | None = None
    while True:
        result = await backend.list_all_recall_files(cursor=cursor)
        listed += len(result["recall_files"])
        if progress is not None:
            progress(listed)
        for recall_file in result["recall_files"]:
            subdir = TRACK_DIRS.get(recall_file.get("track"))
            if subdir is not None:
                write_recall_file(workspace.base, subdir, recall_file)
        cursor = result.get("next_cursor")
        if not cursor:
            return listed


def prepare_run(workspace: RunWorkspace, num_sessions: int, *, verify_command: str) -> None:
    """Snapshot a store-derived mirror and generate the ordered evolve jobs."""
    from memu.hosts import templates
    from memu.hosts.bridging.instructions import MEMORY_JOB_TEMPLATE, SKILL_JOB_TEMPLATE, prepare_instruction_jobs
    from memu.hosts.bridging.manifest import snapshot_tracked
    from memu.hosts.bridging.resources import RESOURCE_JOB_TEMPLATE, prepare_resource_job

    if not workspace.manifest.exists():
        snapshot_tracked(workspace.base, workspace.track_dirs, workspace.manifest)
    workspace.resource_log.unlink(missing_ok=True)
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
    if num_sessions:
        prepare_resource_job(
            job_dir=workspace.jobs,
            verify_command=verify_command,
            resource_file=workspace.resources,
            job_index=2 * num_sessions + 1,
            template=templates.resolve(templates.RESOURCE_JOB, RESOURCE_JOB_TEMPLATE),
        )


async def submit_run(workspace: RunWorkspace, backend: AgenticMemoryBackend) -> dict[str, Any]:
    from memu.hosts.bridging.manifest import diff_tracked
    from memu.hosts.bridging.recall_files import read_recall_file
    from memu.hosts.bridging.resources import read_resources

    subdir_track = {subdir: track for track, subdir in TRACK_DIRS.items()}
    changed = diff_tracked(workspace.base, workspace.track_dirs, workspace.manifest)
    recall_files = [read_recall_file(path, subdir_track[path.relative_to(workspace.base).parts[0]]) for path in changed]
    return await backend.commit_results(recall_files=recall_files, resource=read_resources(workspace.resources))


def read_receipt(workspace: RunWorkspace) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(workspace.receipt.read_text(encoding="utf-8"))
    return result


async def commit_run(workspace: RunWorkspace, backend: AgenticMemoryBackend) -> dict[str, Any]:
    """Persist an acknowledged submission so finalization can retry locally.

    An exception before the receipt lands can still have an unknown outcome.
    Callers must not automatically resubmit such a run.
    """
    if workspace.receipt.exists():
        return read_receipt(workspace)
    result = await submit_run(workspace, backend)
    try:
        atomic_write_text(workspace.receipt, json.dumps(result, ensure_ascii=False) + "\n")
    except OSError as exc:
        msg = f"run committed, but could not persist its receipt at {workspace.base}; do not resubmit: {exc}"
        raise RuntimeError(msg) from exc
    return result


def finish_run(workspace: RunWorkspace) -> None:
    """Update the baseline and clear completed jobs and input slices."""
    from memu.hosts.bridging.manifest import snapshot_tracked

    snapshot_tracked(workspace.base, workspace.track_dirs, workspace.manifest)
    for stale in workspace.jobs.glob("*.txt"):
        stale.unlink()
    for stale in workspace.input.glob("*.jsonl"):
        stale.unlink()
    workspace.resource_log.unlink(missing_ok=True)
