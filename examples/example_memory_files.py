"""
Example: Memory File System (INDEX.md / MEMORY.md / skill/)

This example demonstrates the `memu.memory_fs` export layer that is documented in
docs/architecture.md. `memorize()` ingests a *folder*: it scans the directory,
infers each file's modality by extension, diffs against a sidecar
`.memu_manifest.json`, and incrementally syncs memory. The browsable markdown
tree is always (re)built on every call, so it stays current automatically:

    <output_dir>/
    ├── INDEX.md                  ← index of the raw files under resource/
    ├── MEMORY.md                 ← overall overview + index of memory/
    ├── SKILL.md                  ← index/description of the skills under skill/
    ├── resource/<file_name>      ← one copied raw source file
    ├── memory/<slug>.md          ← one memory category (description + summary)
    └── skill/<slug>/SKILL.md     ← one skill profile extracted during memorize

Usage:
    export OPENAI_API_KEY=your_api_key
    python examples/example_memory_files.py
"""

import asyncio
import os
import pathlib
import shutil

from memu.app import MemoryService

OUTPUT_DIR = "examples/output/memory_files_example"

# Repo-bundled sample folder so the example runs without extra setup.
SOURCE_FOLDER = "examples/resources/conversations"
# Working copy memorize() syncs (so the input-side .memu_manifest.json is not
# written into the tracked resources folder). memorize() scans this directory and
# infers each file's modality from its extension.
INPUT_FOLDER = "examples/output/memory_files_example_input"


def print_tree(root: str) -> None:
    """Print every generated artifact (relative path + its full content)."""
    base = pathlib.Path(root)
    if not base.exists():
        print(f"(nothing written to {root})")
        return
    files = sorted(p for p in base.rglob("*") if p.is_file())
    for path in files:
        rel = path.relative_to(base)
        print("\n" + "=" * 70)
        print(f"# {rel}")
        print("=" * 70)
        # Skip dumping the sidecar manifest body; just note that it exists.
        if path.name == ".memufs_manifest.json":
            print("(diff-detection manifest)")
            continue
        print(path.read_text(encoding="utf-8").rstrip())


async def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        msg = "Please set OPENAI_API_KEY environment variable"
        raise ValueError(msg)

    # The memory file tree is always built/updated on every memorize(). Here we
    # only override output_dir so the demo does not write to the default
    # ./data/memory. MEMORY.md is rendered deterministically from category
    # summaries by default (the skill/ tree is built from the skill-type memories
    # extracted during memorize); set synthesize=True to synthesize MEMORY.md from
    # descriptions instead.
    service = MemoryService(
        llm_profiles={
            "default": {
                "api_key": api_key,
                "chat_model": "gpt-4o-mini",
            },
        },
        memory_files_config={
            "output_dir": OUTPUT_DIR,
        },
    )

    if not os.path.isdir(SOURCE_FOLDER):
        msg = f"Sample folder not found: {SOURCE_FOLDER}"
        raise FileNotFoundError(msg)
    shutil.copytree(SOURCE_FOLDER, INPUT_FOLDER, dirs_exist_ok=True)

    print(f"Memorizing sample folder (tree initializes, then updates): {INPUT_FOLDER}")
    result = await service.memorize(folder=INPUT_FOLDER)
    print(f"  added={result['added']} modified={result['modified']} deleted={result['deleted']}")
    print(f"  {len(result.get('items', []))} items extracted across {len(result['resources'])} files")

    print("\nGenerated memory file tree:")
    print_tree(OUTPUT_DIR)


if __name__ == "__main__":
    asyncio.run(main())
