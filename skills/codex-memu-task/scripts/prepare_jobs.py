import asyncio
import os
from pathlib import Path

# Running this file directly puts its own directory on sys.path, so the sibling
# `lib` package resolves wherever this folder is dropped — no install needed.
from utils.instructions import prepare_instruction_jobs
from utils.manifest import snapshot_tracked
from utils.recall_files import write_recall_file
from utils.resources import prepare_resource_job
from utils.sessions import prepare_session_jobs

from memu.app import MemoryService

MEMU_BASE_DIR = "~/.memu"
RAW_SESSION_DIR = "~/.codex/sessions"

TRACK_DIRS = {
    "memory": "memory",
    "skill": "skill",
}
RES_SESSION_DIR = "sessions"
JOB_DIR = "jobs"
SESSION_MANIFEST_FILE = ".session_manifest.json"
MEMORY_MANIFEST_FILE = ".memory_manifest.json"

TEMP_RESOURCE_FILE = ".resource.tmp"
OUTPUT_RESOURCE_FILE = "resources.md"

VERIFY_RESOURCES_SCRIPT = "verify_resources.py"

MAX_JOBS = 10
MAX_RESOURCE = 50


async def main() -> None:
    base_dir = Path(os.path.expanduser(MEMU_BASE_DIR))
    session_dir = base_dir / RES_SESSION_DIR

    # Step 1 — prepare sessions: slice new raw session turns into numbered jsonl inputs.
    num_sessions = prepare_session_jobs(
        raw_dir=Path(os.path.expanduser(RAW_SESSION_DIR)),
        out_dir=session_dir,
        manifest_path=base_dir / SESSION_MANIFEST_FILE,
        max_jobs=MAX_JOBS,
    )

    # Step 2 — prepare memory files: mirror current recall files to disk as markdown.
    service = MemoryService()  # fill in config if needed
    result = await service.list_all_recall_files()
    for recall_file in result["categories"]:
        subdir = TRACK_DIRS.get(recall_file.get("track"))
        if subdir is None:
            continue
        write_recall_file(base_dir, subdir, recall_file)

    # Snapshot the mirrored files by content hash so the collector (step 3) can
    # tell which ones the agent went on to create or modify.
    snapshot_tracked(base_dir, list(TRACK_DIRS.values()), base_dir / MEMORY_MANIFEST_FILE)

    # Step 3 — build job files: fill the instruction templates with concrete paths.
    prepare_instruction_jobs(
        job_dir=base_dir / JOB_DIR,
        session_dir=session_dir,
        memory_dir=base_dir / TRACK_DIRS["memory"],
        skill_dir=base_dir / TRACK_DIRS["skill"],
        resource_log=base_dir / TEMP_RESOURCE_FILE,
        num_sessions=num_sessions,
    )
    prepare_resource_job(
        job_dir=base_dir / JOB_DIR,
        script_path=Path(__file__).resolve().parent / VERIFY_RESOURCES_SCRIPT,
        resource_file=base_dir / OUTPUT_RESOURCE_FILE,
        job_index=2 * num_sessions + 1,
    )


if __name__ == "__main__":
    asyncio.run(main())
