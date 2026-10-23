"""Host transcript/cursor adapter over the shared run lifecycle."""

from __future__ import annotations

import os
import time
from collections.abc import Collection
from typing import Any

from memu import events
from memu.env import build_agentic_memory_backend_from_env
from memu.hosts import templates  # noqa: F401 -- existing template override seam
from memu.hosts.base import TranscriptSource
from memu.hosts.bridging.layout import Layout
from memu.hosts.bridging.transcripts import prepare_transcripts
from memu.run import commit_run, finish_run, mirror_run, prepare_run, read_receipt, submit_run

MAX_JOBS = 10


async def prepare(
    source: TranscriptSource,
    layout: Layout,
    *,
    verify_command: str,
    max_jobs: int = MAX_JOBS,
    skip_sessions: Collection[str] = (),
    host: str = "",
    session_id_env: str = "",
) -> int:
    num_sessions = prepare_transcripts(
        source,
        out_dir=layout.sessions,
        manifest_path=layout.session_manifest,
        max_jobs=max_jobs,
        pending_path=layout.session_manifest_pending,
        skip_sessions=skip_sessions,
    )
    backend = build_agentic_memory_backend_from_env()
    started = time.monotonic()
    listed = 0

    def progress(count: int) -> None:
        nonlocal listed
        listed = count

    try:
        await mirror_run(backend, layout, progress=progress)
    except Exception:
        events.record_list(started=started, listed=listed, success=False, host=host, session_id_env=session_id_env)
        raise
    events.record_list(started=started, listed=listed, success=True, host=host, session_id_env=session_id_env)
    for subdir in layout.track_dirs:
        (layout.base / subdir).mkdir(parents=True, exist_ok=True)
    prepare_run(layout, num_sessions, verify_command=verify_command)
    return num_sessions


async def commit(layout: Layout) -> dict[str, Any]:
    """Submit a run and then promote host progress; receipt retries only finalize."""
    private = (layout.base / ".run.json").exists()
    if private and layout.receipt.exists():
        result = read_receipt(layout)
    else:
        backend = build_agentic_memory_backend_from_env()
        result = await commit_run(layout, backend) if private else await submit_run(layout, backend)
    # The pending file stays in place until replacement succeeds. Once it is
    # promoted, a finalization retry must not replace it with another run's state.
    pending = layout.session_manifest_pending
    if pending.exists():
        layout.session_manifest.parent.mkdir(parents=True, exist_ok=True)
        os.replace(pending, layout.session_manifest)
    finish_run(layout)
    return result
