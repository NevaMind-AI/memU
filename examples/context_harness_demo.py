"""
Folder-backed context harness demo.

Run from the repository root:

    python examples/context_harness_demo.py

This demo does not require an API key. It uses deterministic local extraction,
sidecar evidence for a fake screenshot, and a promoted manual skill note.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from memu import ContextHarness, FolderMemoryCompilerConfig, SkillToolTrace


def main() -> None:
    base_dir = ROOT / "examples" / "output" / "context_harness_demo"
    upload_dir = base_dir / "upload"
    repo_dir = base_dir / "memory_repo"

    if base_dir.exists():
        shutil.rmtree(base_dir)
    upload_dir.mkdir(parents=True)

    (upload_dir / "profile.txt").write_text(
        "The user prefers calm, concise answers. "
        "Skill: validate generated context before relying on it.",
        encoding="utf-8",
    )
    (upload_dir / "workflow.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (upload_dir / "workflow.caption.md").write_text(
        "Skill: inspect screenshots and compare them against acceptance criteria.",
        encoding="utf-8",
    )

    config = FolderMemoryCompilerConfig(use_memory_service=False)
    upload_harness = ContextHarness(upload_dir, repo_dir, compiler_config=config)
    upload_harness.scaffold(copy_source=True)

    harness = ContextHarness.from_repo(repo_dir, compiler_config=config)
    run = harness.refresh_context_sync(query="context validation workflow")

    harness.record_skill_trace_sync(
        task="Validate generated context packs",
        outcome="success",
        summary="Compiled raw data, built a context pack, and checked skill sections.",
        actions=["Compile raw data", "Build context pack", "Inspect skill sections"],
        tools=[SkillToolTrace(name="memu-harness", success=True, score=0.95)],
        lessons=["Inspect generated and promoted skill sections before using context."],
    )
    harness.promote_skill(
        title="Validate Context Packs",
        when_to_use="Before injecting generated context into an agent.",
        actions=["Build the context pack", "Check generated and promoted skill sections"],
        lessons=["Inspect promoted skills before relying on generated context."],
        tags=["context", "validation"],
    )

    context = harness.build_context_markdown(query="context validation workflow", max_chars=4000)
    print("memU context harness demo complete")
    print(f"  repo: {repo_dir}")
    print(f"  processed: {run.compile_result.processed}")
    print(f"  memory: {repo_dir / 'memory.md'}")
    print(f"  soul: {repo_dir / 'soul.md'}")
    print(f"  skill: {repo_dir / 'skill.md'}")
    print("\n--- Context Pack Preview ---")
    print(context)


if __name__ == "__main__":
    main()
