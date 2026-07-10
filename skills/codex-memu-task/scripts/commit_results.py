import asyncio
import os
from pathlib import Path

# See prepare_jobs.py for why importing the sibling `lib` package works standalone.
from utils.manifest import diff_tracked
from utils.recall_files import read_recall_file
from utils.resources import read_resources

from memu.app import MemoryService

MEMU_BASE_DIR = "~/.memu"

# Must match prepare_jobs.py: same tracks, same manifest, same resource file.
TRACK_DIRS = {
    "memory": "memory",
    "skill": "skill",
}
MEMORY_MANIFEST_FILE = ".memory_manifest.json"
OUTPUT_RESOURCE_FILE = "resources.md"


async def main() -> None:
    base_dir = Path(os.path.expanduser(MEMU_BASE_DIR))
    subdir_track = {subdir: track for track, subdir in TRACK_DIRS.items()}

    # Recall files the agent created or modified since the step-1 snapshot,
    # parsed back into {name, track, description, content}.
    changed = diff_tracked(
        base_dir,
        list(TRACK_DIRS.values()),
        base_dir / MEMORY_MANIFEST_FILE,
    )
    recall_files = [read_recall_file(path, subdir_track[path.relative_to(base_dir).parts[0]]) for path in changed]

    # Resources the agent described, minus the ones it marked `null`.
    resources = read_resources(base_dir / OUTPUT_RESOURCE_FILE)

    service = MemoryService()  # fill in config if needed
    await service.commit_results(recall_files=recall_files, resource=resources)


if __name__ == "__main__":
    asyncio.run(main())
