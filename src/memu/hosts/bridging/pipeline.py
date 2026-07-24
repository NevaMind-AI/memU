"""The record seam: prepare -> (the agent self-evolves) -> commit.

Three steps, of which only the first and last are code. The middle step is real
agent work — reading transcripts, making judgement calls, writing markdown — so
prepare's job is to leave behind a set of self-contained instruction files, and
commit's job is to pick up whatever the agent actually left on disk.

Nothing here knows what a Codex is. The host arrives as a
:class:`~memu.hosts.base.TranscriptSource`.
"""

from __future__ import annotations

import os
from typing import Any

from memu.env import build_agentic_memory_backend_from_env
from memu.hosts.base import TranscriptSource
from memu.hosts.bridging.instructions import prepare_instruction_jobs
from memu.hosts.bridging.layout import TRACK_DIRS, Layout
from memu.hosts.bridging.manifest import diff_tracked, snapshot_tracked
from memu.hosts.bridging.recall_files import read_recall_file, write_recall_file
from memu.hosts.bridging.resources import prepare_resource_job, read_resources
from memu.hosts.bridging.transcripts import prepare_transcripts

MAX_JOBS = 10


async def prepare(
    source: TranscriptSource,
    layout: Layout,
    *,
    verify_command: str,
    max_jobs: int = MAX_JOBS,
) -> int:
    """Regenerate the job files from whatever the host has logged since last run.

    Returns the number of sessions prepared. Zero is a correct, common outcome —
    a scheduled run on a day with no new sessions has nothing to do.
    """
    num_sessions = prepare_transcripts(
        source,
        out_dir=layout.sessions,
        manifest_path=layout.session_manifest,
        max_jobs=max_jobs,
        pending_path=layout.session_manifest_pending,
    )

    # Mirror the store's current recall files to disk. The snapshot is only
    # *bootstrapped* here (first contact, from store-derived — i.e. committed —
    # content); afterwards it is re-taken by a successful commit and means
    # "state as of the last commit". Re-snapshotting on every prepare would
    # absorb files a crashed run wrote but never committed, making them
    # undiffable — and therefore uncommittable — forever.
    backend = build_agentic_memory_backend_from_env()
    result = await backend.list_all_recall_files()
    for recall_file in result["categories"]:
        subdir = TRACK_DIRS.get(recall_file.get("track"))
        if subdir is None:
            continue
        write_recall_file(layout.base, subdir, recall_file)
    if not layout.memory_manifest.exists():
        snapshot_tracked(layout.base, layout.track_dirs, layout.memory_manifest)

    # The touched-file log is per-run. Left in place it accumulates across runs,
    # and since the verify pass caps at the first N paths, stale entries would
    # eventually crowd out every file the current run actually touched.
    layout.resource_log.unlink(missing_ok=True)

    prepare_instruction_jobs(
        job_dir=layout.jobs,
        session_dir=layout.sessions,
        memory_dir=layout.memory,
        skill_dir=layout.skill,
        resource_log=layout.resource_log,
        num_sessions=num_sessions,
    )
    prepare_resource_job(
        job_dir=layout.jobs,
        verify_command=verify_command,
        resource_file=layout.resources,
        job_index=2 * num_sessions + 1,
    )
    return num_sessions


async def commit(layout: Layout) -> dict[str, Any]:
    """Submit whatever the agent created or changed, then make the run durable.

    State advances on durable success, not on intent (#518): the session
    cursor staged by ``prepare`` is promoted here, and the memory snapshot is
    re-taken here — both strictly after the store accepted the submission. A
    run that dies anywhere earlier leaves the previous cursor and snapshot in
    force, so everything unfinished is re-offered next time: bounded re-work,
    never silent loss.
    """
    subdir_track = {subdir: track for track, subdir in TRACK_DIRS.items()}

    changed = diff_tracked(layout.base, layout.track_dirs, layout.memory_manifest)
    recall_files = [read_recall_file(path, subdir_track[path.relative_to(layout.base).parts[0]]) for path in changed]
    resources = read_resources(layout.resources)

    backend = build_agentic_memory_backend_from_env()
    result: dict[str, Any] = await backend.commit_results(recall_files=recall_files, resource=resources)

    snapshot_tracked(layout.base, layout.track_dirs, layout.memory_manifest)
    pending = layout.session_manifest_pending
    if pending.exists():
        os.replace(pending, layout.session_manifest)
    return result
