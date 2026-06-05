from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from memu.app import (
    ContextHarness,
    EvolutionReviewConfig,
    FolderMemoryCompiler,
    FolderMemoryCompilerConfig,
    compile_folder_to_markdown_sync,
    watch_folder_to_markdown,
)
from memu.app.context_cli import build_parser as build_context_cli_parser
from memu.app.context_cli import main as context_cli_main
from memu.app.context_harness_cli import build_parser as build_harness_cli_parser
from memu.app.context_harness_cli import main as harness_cli_main
from memu.app.folder_cli import _llm_profile_from_args
from memu.app.folder_cli import build_parser as build_folder_cli_parser
from memu.app.folder_cli import main as folder_cli_main
from memu.app.markdown_context import MarkdownMemoryRepository, inject_context_messages
from memu.app.skill_trace import SkillToolTrace, record_skill_trace
from memu.app.skill_trace_cli import main as skill_trace_cli_main


class FakeMemoryService:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def memorize(self, *, resource_url: str, modality: str, user: dict[str, Any] | None = None) -> dict[str, Any]:
        self.calls.append({"resource_url": resource_url, "modality": modality, "user": user})
        return {
            "resource": {
                "url": resource_url,
                "modality": modality,
                "caption": "A screenshot of a product workflow board.",
            },
            "items": [
                {
                    "memory_type": "profile",
                    "summary": "The user's tone preference is warm and concise.",
                },
                {
                    "memory_type": "skill",
                    "summary": "Use screenshots to infer workflow and tool-use patterns.",
                },
            ],
            "categories": [
                {
                    "name": "workflow",
                    "summary": "Signals about workflows and tool usage.",
                }
            ],
        }


@pytest.mark.asyncio
async def test_compile_creates_markdown_memory_repo_for_multimodal_folder(tmp_path: Path) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / "notes.txt").write_text(
        "The user's tone preference is direct and warm. They like concise answers.",
        encoding="utf-8",
    )
    (source / "workflow.md").write_text(
        "Skill: use pytest to verify code changes. Workflow: inspect, patch, test.",
        encoding="utf-8",
    )
    image_dir = source / "images"
    image_dir.mkdir()
    (image_dir / "screenshot.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    output = tmp_path / "memory_repo"
    compiler = FolderMemoryCompiler(config=FolderMemoryCompilerConfig(use_memory_service=False))

    result = await compiler.compile(source, output)

    assert sorted(result.processed) == ["images/screenshot.png", "notes.txt", "workflow.md"]
    assert (output / "raw_data" / "notes.txt").exists()
    assert (output / "raw_data" / "workflow.md").exists()
    assert (output / "raw_data" / "images" / "screenshot.png").exists()
    assert (output / ".memu" / "derived" / "images" / "screenshot.png.evidence.md").exists()
    assert (output / "memory.md").exists()
    assert (output / "soul.md").exists()
    assert (output / "skill.md").exists()
    assert (output / "AGENTS.md").exists()
    assert (output / "memory").is_dir()
    assert (output / "soul").is_dir()
    assert (output / "skill").is_dir()

    memory_md = (output / "memory.md").read_text(encoding="utf-8")
    soul_md = (output / "soul.md").read_text(encoding="utf-8")
    skill_md = (output / "skill.md").read_text(encoding="utf-8")
    agents_md = (output / "AGENTS.md").read_text(encoding="utf-8")

    assert "<!-- memu:generated:start -->" in memory_md
    assert "raw_data/notes.txt" in memory_md
    assert "raw_data/images/screenshot.png" in memory_md
    assert "soul_" in soul_md
    assert "skill_" in skill_md
    assert "memu-harness context . --query" in agents_md

    manifest = json.loads((output / ".memu" / "manifest.json").read_text(encoding="utf-8"))
    assert sorted(manifest["sources"]) == ["images/screenshot.png", "notes.txt", "workflow.md"]
    assert manifest["sources"]["images/screenshot.png"]["modality"] == "image"


@pytest.mark.asyncio
async def test_compile_routes_entries_through_evolution_review_gate(tmp_path: Path) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / "creator_feedback.md").write_text(
        "Creator feedback: the assistant should keep answers warm and concise.",
        encoding="utf-8",
    )
    output = tmp_path / "memory_repo"
    compiler = FolderMemoryCompiler(config=FolderMemoryCompilerConfig(use_memory_service=False))

    result = await compiler.compile(source, output)

    assert result.entries
    assert result.evolution_instructions
    assert result.patch_proposals
    assert result.review_decisions
    assert all(review.status == "approved" for review in result.review_decisions)

    instruction = result.evolution_instructions[0]
    assert instruction.target in {"memory", "soul", "skill"}
    assert instruction.operation == "add"
    assert instruction.reason
    assert instruction.evidence.source == "raw_data/creator_feedback.md"
    assert instruction.evidence.source_kind == "creator_feedback"

    manifest = json.loads((output / ".memu" / "manifest.json").read_text(encoding="utf-8"))
    source_record = manifest["sources"]["creator_feedback.md"]
    assert source_record["evolution"]["instructions"][0]["id"] == instruction.id
    assert source_record["evolution"]["patch_proposals"][0]["instruction_id"] == instruction.id
    assert source_record["evolution"]["review_decisions"][0]["status"] == "approved"

    evolution_dir = output / ".memu" / "evolution"
    assert (evolution_dir / "instructions.jsonl").exists()
    assert (evolution_dir / "patch_proposals.jsonl").exists()
    assert (evolution_dir / "review_decisions.jsonl").exists()


@pytest.mark.asyncio
async def test_compile_requires_review_before_applying_evolution_patch(tmp_path: Path) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / "agent_log.md").write_text(
        "Agent log: Skill: run focused tests after changing compiler behavior.",
        encoding="utf-8",
    )
    output = tmp_path / "memory_repo"
    compiler = FolderMemoryCompiler(
        config=FolderMemoryCompilerConfig(
            use_memory_service=False,
            evolution_review=EvolutionReviewConfig(auto_approve=False),
        )
    )

    result = await compiler.compile(source, output)

    assert result.evolution_instructions
    assert result.patch_proposals
    assert result.review_decisions
    assert all(review.status == "needs_review" for review in result.review_decisions)
    assert result.entries == []
    assert "run focused tests" not in (output / "skill.md").read_text(encoding="utf-8")

    manifest = json.loads((output / ".memu" / "manifest.json").read_text(encoding="utf-8"))
    source_record = manifest["sources"]["agent_log.md"]
    assert source_record["entries"] == []
    assert source_record["evolution"]["review_decisions"][0]["status"] == "needs_review"

    review_result = compiler.review_evolution(output, reviewer="creator", reason="Approved after review.")

    assert review_result.reviewed
    assert review_result.applied_proposal_ids
    assert any(entry.bucket == "skill" for entry in review_result.entries)
    assert "run focused tests" in (output / "skill.md").read_text(encoding="utf-8")

    reviewed_manifest = json.loads((output / ".memu" / "manifest.json").read_text(encoding="utf-8"))
    reviewed_source = reviewed_manifest["sources"]["agent_log.md"]
    assert reviewed_source["entries"]
    assert reviewed_source["evolution"]["review_decisions"][-1]["status"] == "approved"


@pytest.mark.asyncio
async def test_compile_uses_multimodal_sidecar_evidence(tmp_path: Path) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    image = source / "workflow.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n")
    (source / "workflow.caption.md").write_text(
        "Skill: inspect screenshots to understand a product workflow. "
        "Tone preference: explain findings calmly.",
        encoding="utf-8",
    )
    output = tmp_path / "memory_repo"
    compiler = FolderMemoryCompiler(config=FolderMemoryCompilerConfig(use_memory_service=False))

    result = await compiler.compile(source, output)

    image_entries = [entry for entry in result.entries if entry.source == "raw_data/workflow.png"]
    evidence = (output / ".memu" / "derived" / "workflow.png.evidence.md").read_text(encoding="utf-8")
    soul_md = (output / "soul.md").read_text(encoding="utf-8")
    skill_md = (output / "skill.md").read_text(encoding="utf-8")

    assert {entry.bucket for entry in image_entries} == {"memory", "soul", "skill"}
    assert "## Sidecar Evidence" in evidence
    assert "workflow.caption.md" in evidence
    assert "inspect screenshots" in skill_md
    assert "explain findings calmly" in soul_md


@pytest.mark.asyncio
async def test_compile_uses_structured_json_sidecar_evidence(tmp_path: Path) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    image = source / "workflow.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n")
    (source / "workflow.metadata.json").write_text(
        json.dumps(
            {
                "caption": "Workflow screenshot with acceptance criteria.",
                "lesson": "Skill: compare screenshots against acceptance criteria.",
                "tone": "Tone preference: explain visual findings calmly.",
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "memory_repo"
    compiler = FolderMemoryCompiler(config=FolderMemoryCompilerConfig(use_memory_service=False))

    result = await compiler.compile(source, output)

    evidence = (output / ".memu" / "derived" / "workflow.png.evidence.md").read_text(encoding="utf-8")
    manifest = json.loads((output / ".memu" / "manifest.json").read_text(encoding="utf-8"))
    skill_md = (output / "skill.md").read_text(encoding="utf-8")
    soul_md = (output / "soul.md").read_text(encoding="utf-8")

    assert result.processed == ["workflow.png"]
    assert sorted(manifest["sources"]) == ["workflow.png"]
    assert manifest["sources"]["workflow.png"]["sidecars"] == ["workflow.metadata.json"]
    assert "Structured JSON sidecar" in evidence
    assert "compare screenshots against acceptance criteria" in skill_md
    assert "explain visual findings calmly" in soul_md
    assert (output / "raw_data" / "workflow.metadata.json").exists()


@pytest.mark.asyncio
async def test_compile_uses_document_sidecar_even_when_file_is_utf8_decodable(tmp_path: Path) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    report = source / "report.pdf"
    report.write_text("%PDF-1.7\nASCII-only fake PDF body", encoding="utf-8")
    (source / "report.summary.md").write_text(
        "Skill: summarize PDF evidence before updating context. "
        "Tone preference: explain document findings calmly.",
        encoding="utf-8",
    )
    output = tmp_path / "memory_repo"
    compiler = FolderMemoryCompiler(config=FolderMemoryCompilerConfig(use_memory_service=False))

    result = await compiler.compile(source, output)

    report_entries = [entry for entry in result.entries if entry.source == "raw_data/report.pdf"]
    evidence = (output / ".memu" / "derived" / "report.pdf.evidence.md").read_text(encoding="utf-8")
    manifest = json.loads((output / ".memu" / "manifest.json").read_text(encoding="utf-8"))
    skill_md = (output / "skill.md").read_text(encoding="utf-8")
    soul_md = (output / "soul.md").read_text(encoding="utf-8")

    assert {entry.bucket for entry in report_entries} == {"memory", "soul", "skill"}
    assert "## Multimodal Evidence" in evidence
    assert "## Text Evidence" not in evidence
    assert "report.summary.md" in evidence
    assert manifest["sources"]["report.pdf"]["sidecars"] == ["report.summary.md"]
    assert "summarize PDF evidence" in skill_md
    assert "explain document findings calmly" in soul_md


@pytest.mark.asyncio
async def test_compile_reextracts_media_when_sidecar_changes(tmp_path: Path) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    image = source / "workflow.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n")
    sidecar = source / "workflow.caption.md"
    sidecar.write_text("Skill: inspect screenshots before changing UI workflows.", encoding="utf-8")
    output = tmp_path / "memory_repo"
    compiler = FolderMemoryCompiler(config=FolderMemoryCompilerConfig(use_memory_service=False))

    first = await compiler.compile(source, output)
    first_manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    first_hash = first_manifest["sources"]["workflow.png"]["sha256"]

    sidecar.write_text("Skill: compare screenshots against acceptance criteria.", encoding="utf-8")
    second = await compiler.compile(source, output)
    second_manifest = json.loads(second.manifest_path.read_text(encoding="utf-8"))
    second_hash = second_manifest["sources"]["workflow.png"]["sha256"]
    skill_md = (output / "skill.md").read_text(encoding="utf-8")

    assert first.processed == ["workflow.png"]
    assert sorted(first_manifest["sources"]) == ["workflow.png"]
    assert first_manifest["sources"]["workflow.png"]["sidecars"] == ["workflow.caption.md"]
    assert second.processed == ["workflow.png"]
    assert second_hash != first_hash
    assert "compare screenshots" in skill_md
    assert "changing UI workflows" not in skill_md
    assert (output / "raw_data" / "workflow.caption.md").exists()


@pytest.mark.asyncio
async def test_compile_excludes_configured_source_patterns(tmp_path: Path) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / "notes.txt").write_text("Skill: keep meaningful source files.", encoding="utf-8")
    (source / "debug.tmp").write_text("Temporary debug output.", encoding="utf-8")
    cache_dir = source / "node_modules" / "pkg"
    cache_dir.mkdir(parents=True)
    (cache_dir / "cache.txt").write_text("Dependency cache.", encoding="utf-8")
    image = source / "workflow.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n")
    (source / "workflow.metadata.json").write_text(
        '{"lesson":"Skill: excluded sidecar should not be used."}',
        encoding="utf-8",
    )
    output = tmp_path / "memory_repo"
    compiler = FolderMemoryCompiler(
        config=FolderMemoryCompilerConfig(
            use_memory_service=False,
            exclude_patterns=("node_modules/**", "*.tmp", "*.metadata.json"),
        )
    )

    result = await compiler.compile(source, output)

    manifest = json.loads((output / ".memu" / "manifest.json").read_text(encoding="utf-8"))
    skill_md = (output / "skill.md").read_text(encoding="utf-8")
    assert sorted(result.processed) == ["notes.txt", "workflow.png"]
    assert sorted(manifest["sources"]) == ["notes.txt", "workflow.png"]
    assert manifest["sources"]["workflow.png"]["sidecars"] == []
    assert not (output / "raw_data" / "debug.tmp").exists()
    assert not (output / "raw_data" / "node_modules").exists()
    assert not (output / "raw_data" / "workflow.metadata.json").exists()
    assert "excluded sidecar" not in skill_md


@pytest.mark.asyncio
async def test_compile_uses_source_memuignore_patterns(tmp_path: Path) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / ".memuignore").write_text("node_modules/**\n*.tmp\n", encoding="utf-8")
    (source / "notes.txt").write_text("Skill: keep meaningful source files.", encoding="utf-8")
    (source / "debug.tmp").write_text("Temporary debug output.", encoding="utf-8")
    cache_dir = source / "node_modules" / "pkg"
    cache_dir.mkdir(parents=True)
    (cache_dir / "cache.txt").write_text("Dependency cache.", encoding="utf-8")
    output = tmp_path / "memory_repo"
    compiler = FolderMemoryCompiler(config=FolderMemoryCompilerConfig(use_memory_service=False))

    result = await compiler.compile(source, output)

    manifest = json.loads((output / ".memu" / "manifest.json").read_text(encoding="utf-8"))
    assert result.processed == ["notes.txt"]
    assert sorted(manifest["sources"]) == ["notes.txt"]
    assert not (output / "raw_data" / ".memuignore").exists()
    assert not (output / "raw_data" / "debug.tmp").exists()
    assert not (output / "raw_data" / "node_modules").exists()


@pytest.mark.asyncio
async def test_compile_reextracts_changed_files_and_preserves_manual_markdown(tmp_path: Path) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    profile = source / "profile.txt"
    profile.write_text("The user prefers concise answers.", encoding="utf-8")
    output = tmp_path / "memory_repo"
    compiler = FolderMemoryCompiler(config=FolderMemoryCompilerConfig(use_memory_service=False))

    first = await compiler.compile(source, output)
    first_hash = json.loads(first.manifest_path.read_text(encoding="utf-8"))["sources"]["profile.txt"]["sha256"]
    memory_path = output / "memory.md"
    memory_path.write_text(
        memory_path.read_text(encoding="utf-8") + "\nManual note kept by the user.\n",
        encoding="utf-8",
    )

    profile.write_text("The user prefers detailed answers.", encoding="utf-8")
    second = await compiler.compile(source, output)

    second_hash = json.loads(second.manifest_path.read_text(encoding="utf-8"))["sources"]["profile.txt"]["sha256"]
    memory_md = memory_path.read_text(encoding="utf-8")

    assert second.processed == ["profile.txt"]
    assert second_hash != first_hash
    assert "detailed answers" in memory_md
    assert "concise answers" not in memory_md
    assert "Manual note kept by the user." in memory_md


@pytest.mark.asyncio
async def test_compile_removes_deleted_source_memory_and_raw_copy(tmp_path: Path) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    obsolete = source / "obsolete.txt"
    obsolete.write_text("A temporary memory that should disappear.", encoding="utf-8")
    output = tmp_path / "memory_repo"
    compiler = FolderMemoryCompiler(config=FolderMemoryCompilerConfig(use_memory_service=False))

    await compiler.compile(source, output)
    evidence_path = output / ".memu" / "derived" / "obsolete.txt.evidence.md"
    assert evidence_path.exists()
    obsolete.unlink()
    result = await compiler.compile(source, output)

    manifest = json.loads((output / ".memu" / "manifest.json").read_text(encoding="utf-8"))
    memory_md = (output / "memory.md").read_text(encoding="utf-8")

    assert result.removed == ["obsolete.txt"]
    assert manifest["sources"] == {}
    assert not (output / "raw_data" / "obsolete.txt").exists()
    assert not evidence_path.exists()
    assert "raw_data/obsolete.txt" not in memory_md


@pytest.mark.asyncio
async def test_compile_preserves_manual_bucket_detail_files(tmp_path: Path) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    note = source / "notes.txt"
    note.write_text("Skill: preserve manual skill cards.", encoding="utf-8")
    output = tmp_path / "memory_repo"
    compiler = FolderMemoryCompiler(config=FolderMemoryCompilerConfig(use_memory_service=False))

    await compiler.compile(source, output)

    manual_card = output / "skill" / "manual-card.md"
    manual_card.write_text("# Manual Skill Card\n\nKeep this hand-written skill.", encoding="utf-8")
    generated_card = output / "skill" / "notes.txt.md"
    generated_card.write_text(
        generated_card.read_text(encoding="utf-8") + "\nManual note on stale generated card.\n",
        encoding="utf-8",
    )
    note.unlink()

    await compiler.compile(source, output)

    assert manual_card.exists()
    assert "Keep this hand-written skill" in manual_card.read_text(encoding="utf-8")
    assert generated_card.exists()
    stale_text = generated_card.read_text(encoding="utf-8")
    assert "Manual note on stale generated card" in stale_text
    assert "Skill: preserve manual skill cards" not in stale_text


@pytest.mark.asyncio
async def test_compile_same_source_and_output_uses_repo_raw_data(tmp_path: Path) -> None:
    upload = tmp_path / "upload"
    upload.mkdir()
    (upload / "notes.txt").write_text("Skill: refresh a repository from raw_data.", encoding="utf-8")
    output = tmp_path / "memory_repo"
    compiler = FolderMemoryCompiler(config=FolderMemoryCompilerConfig(use_memory_service=False))

    compiler.scaffold(output, source_folder=upload)
    (output / "root-note.md").write_text("This repo note should not become raw data.", encoding="utf-8")
    result = await compiler.compile(output, output)
    status = compiler.status(output, output)
    fingerprint = compiler.source_fingerprint(output, output)

    memory_md = (output / "memory.md").read_text(encoding="utf-8")
    assert result.processed == ["notes.txt"]
    assert status.source_dir == (output / "raw_data").resolve()
    assert fingerprint[0][0] == "notes.txt"
    assert (output / "raw_data" / "notes.txt").exists()
    assert (output / "root-note.md").exists()
    assert "root-note.md" not in memory_md
    assert "refresh a repository from raw_data" in memory_md


@pytest.mark.asyncio
async def test_compile_excludes_output_repo_inside_source_folder(tmp_path: Path) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / "notes.txt").write_text("Skill: keep output repo out of raw data.", encoding="utf-8")
    output = source / "memory_repo"
    compiler = FolderMemoryCompiler(config=FolderMemoryCompilerConfig(use_memory_service=False))

    first = await compiler.compile(source, output)
    second = await compiler.compile(source, output)
    manifest = json.loads((output / ".memu" / "manifest.json").read_text(encoding="utf-8"))

    assert first.processed == ["notes.txt"]
    assert second.skipped == ["notes.txt"]
    assert sorted(manifest["sources"]) == ["notes.txt"]
    assert not (output / "raw_data" / "memory_repo").exists()
    assert "memory_repo/" not in (output / "memory.md").read_text(encoding="utf-8")


def test_scaffold_excludes_output_repo_inside_source_folder(tmp_path: Path) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / "notes.txt").write_text("Raw source note.", encoding="utf-8")
    output = source / "memory_repo"
    compiler = FolderMemoryCompiler(config=FolderMemoryCompilerConfig(use_memory_service=False))

    result = compiler.scaffold(output, source_folder=source)

    assert result.copied == ["notes.txt"]
    assert (output / "raw_data" / "notes.txt").exists()
    assert not (output / "raw_data" / "memory_repo").exists()


@pytest.mark.asyncio
async def test_compile_uses_memory_service_and_writes_service_evidence(tmp_path: Path) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    image = source / "workflow.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n")
    output = tmp_path / "memory_repo"
    service = FakeMemoryService()
    compiler = FolderMemoryCompiler(memory_service=service)

    result = await compiler.compile(source, output, user={"user_id": "u1"})

    assert service.calls == [
        {
            "resource_url": str(image.resolve()),
            "modality": "image",
            "user": {"user_id": "u1"},
        }
    ]
    assert [entry.bucket for entry in result.entries] == ["soul", "skill"]
    assert all("llm-extracted" in entry.tags for entry in result.entries)

    evidence = (output / ".memu" / "derived" / "workflow.png.evidence.md").read_text(encoding="utf-8")
    assert "## MemoryService Extraction" in evidence
    assert "A screenshot of a product workflow board." in evidence
    assert "Use screenshots to infer workflow and tool-use patterns." in evidence

    soul_md = (output / "soul.md").read_text(encoding="utf-8")
    skill_md = (output / "skill.md").read_text(encoding="utf-8")
    memory_md = (output / "memory.md").read_text(encoding="utf-8")
    assert "warm and concise" in soul_md
    assert "workflow and tool-use patterns" in skill_md
    assert "workflow.png" not in memory_md


def test_folder_cli_compiles_to_json_summary(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / "notes.txt").write_text("Skill: inspect files, patch code, and run tests.", encoding="utf-8")
    output = tmp_path / "memory_repo"

    exit_code = folder_cli_main([str(source), str(output), "--json", "--user", "user_id=u1"])

    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert exit_code == 0
    assert summary["processed"] == ["notes.txt"]
    assert summary["entry_count"] >= 1
    assert summary["entries_by_bucket"]["skill"] == 1
    assert (output / "raw_data" / "notes.txt").exists()
    assert (output / "skill.md").exists()


def test_folder_cli_grok_profile_defaults_to_xai_key_env() -> None:
    parser = build_folder_cli_parser()
    args = parser.parse_args(["source", "output", "--use-memory-service", "--provider", "grok"])

    profile = _llm_profile_from_args(args)

    assert profile["provider"] == "grok"
    assert profile["api_key"] == "XAI_API_KEY"


def test_folder_cli_api_key_env_overrides_provider_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CUSTOM_KEY_ENV", "resolved-key")
    parser = build_folder_cli_parser()
    args = parser.parse_args(
        [
            "source",
            "output",
            "--use-memory-service",
            "--provider",
            "grok",
            "--api-key-env",
            "CUSTOM_KEY_ENV",
        ]
    )

    profile = _llm_profile_from_args(args)

    assert profile["api_key"] == "resolved-key"


def test_harness_cli_grok_profile_defaults_to_xai_key_env() -> None:
    parser = build_harness_cli_parser()
    args = parser.parse_args(["refresh", "source", "output", "--use-memory-service", "--provider", "grok"])

    profile = _llm_profile_from_args(args)

    assert profile["api_key"] == "XAI_API_KEY"


def test_cli_positive_numeric_args_reject_non_positive_values() -> None:
    invalid_invocations = [
        (build_folder_cli_parser(), ["source", "output", "--max-text-chars", "0"]),
        (build_folder_cli_parser(), ["source", "output", "--watch", "--poll-interval", "0"]),
        (build_folder_cli_parser(), ["source", "output", "--watch", "--watch-max-runs", "-1"]),
        (build_folder_cli_parser(), ["source", "output", "--min-evolution-confidence", "1.1"]),
        (build_harness_cli_parser(), ["init", "repo", "--max-text-chars", "0"]),
        (build_harness_cli_parser(), ["refresh", "repo", "--max-chars", "0"]),
        (build_harness_cli_parser(), ["watch", "repo", "--poll-interval", "-0.5"]),
        (build_harness_cli_parser(), ["suggest-skills", "repo", "--limit", "0"]),
        (build_harness_cli_parser(), ["refresh", "repo", "--min-evolution-confidence", "-0.1"]),
        (build_context_cli_parser(), ["repo", "--max-chars", "0"]),
    ]

    for parser, args in invalid_invocations:
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(args)
        assert exc_info.value.code == 2


@pytest.mark.asyncio
async def test_watch_folder_recompiles_after_source_change(tmp_path: Path) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    profile = source / "profile.txt"
    profile.write_text("The user prefers concise answers.", encoding="utf-8")
    output = tmp_path / "memory_repo"

    async def mutate_after_initial(event) -> None:
        if event.reason == "initial":
            profile.write_text("The user prefers detailed answers.", encoding="utf-8")

    events = await watch_folder_to_markdown(
        source,
        output,
        config=FolderMemoryCompilerConfig(use_memory_service=False),
        poll_interval=0.01,
        max_runs=2,
        on_event=mutate_after_initial,
    )

    memory_md = (output / "memory.md").read_text(encoding="utf-8")
    assert [event.reason for event in events] == ["initial", "changed"]
    assert events[0].status is not None
    assert events[0].status.new == ["profile.txt"]
    assert events[1].status is not None
    assert events[1].status.changed == ["profile.txt"]
    assert events[1].result.processed == ["profile.txt"]
    assert "detailed answers" in memory_md
    assert "concise answers" not in memory_md


def test_folder_cli_watch_outputs_json_event(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / "notes.txt").write_text("Skill: run focused validation after edits.", encoding="utf-8")
    output = tmp_path / "memory_repo"

    exit_code = folder_cli_main(
        [
            str(source),
            str(output),
            "--watch",
            "--watch-max-runs",
            "1",
            "--poll-interval",
            "0.01",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    event = json.loads(captured.out)
    assert exit_code == 0
    assert event["reason"] == "initial"
    assert event["iteration"] == 1
    assert event["processed"] == ["notes.txt"]
    assert event["delta"]["new"] == ["notes.txt"]
    assert event["delta"]["counts"]["new"] == 1


@pytest.mark.asyncio
async def test_markdown_context_loader_reads_generated_and_manual_notes(tmp_path: Path) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / "notes.txt").write_text(
        "The user's tone preference is direct. Skill: inspect files before patching.",
        encoding="utf-8",
    )
    output = tmp_path / "memory_repo"
    compiler = FolderMemoryCompiler(config=FolderMemoryCompilerConfig(use_memory_service=False))

    await compiler.compile(source, output)
    soul_path = output / "soul.md"
    soul_path.write_text(
        soul_path.read_text(encoding="utf-8") + "\nManual soul note: keep answers calm and compact.\n",
        encoding="utf-8",
    )

    repo = MarkdownMemoryRepository(output)
    sections = repo.list_sections()
    pack = repo.build_context_pack(query="tone and patching", max_chars=3000)

    assert any(section.kind == "generated" and section.bucket == "skill" for section in sections)
    assert any(section.kind == "manual" and "calm and compact" in section.content for section in sections)
    assert not any(section.kind == "manual" and section.content.startswith("# Skill From") for section in sections)
    assert "Manual soul note" in pack.to_markdown()
    assert "inspect files before patching" in pack.to_markdown()


def test_context_cli_outputs_json_pack(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / "notes.txt").write_text("Skill: run focused validation after edits.", encoding="utf-8")
    output = tmp_path / "memory_repo"
    folder_cli_main([str(source), str(output)])
    capsys.readouterr()

    exit_code = context_cli_main([str(output), "--query", "validation", "--json"])

    captured = capsys.readouterr()
    pack = json.loads(captured.out)
    assert exit_code == 0
    assert pack["query"] == "validation"
    assert pack["sections"]
    assert any(section["bucket"] == "skill" for section in pack["sections"])


def test_context_cli_writes_rendered_context_to_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / "notes.txt").write_text("Skill: run focused validation after edits.", encoding="utf-8")
    output = tmp_path / "memory_repo"
    context_path = tmp_path / "artifacts" / "context.system.md"
    folder_cli_main([str(source), str(output)])
    capsys.readouterr()

    exit_code = context_cli_main(
        [
            str(output),
            "--query",
            "validation",
            "--format",
            "system",
            "--output",
            str(context_path),
        ]
    )

    captured = capsys.readouterr()
    rendered = context_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert captured.out == ""
    assert "<memu_context_instructions>" in rendered
    assert "run focused validation after edits" in rendered


def test_context_pack_exports_summary(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / "notes.txt").write_text("Skill: summarize context sections for agents.", encoding="utf-8")
    output = tmp_path / "memory_repo"
    folder_cli_main([str(source), str(output)])
    capsys.readouterr()

    pack = MarkdownMemoryRepository(output).build_context_pack(query="context summary")
    summary = pack.to_summary()

    assert summary["section_count"] == len(pack.sections)
    assert summary["buckets"]["memory"] >= 1
    assert summary["buckets"]["skill"] >= 1
    assert summary["kinds"]["generated"] >= 1
    assert "raw_data/notes.txt" in summary["sources"]
    assert "content" not in summary["sections"][0]

    assert context_cli_main([str(output), "--query", "context summary", "--format", "summary"]) == 0
    captured = capsys.readouterr()
    cli_summary = json.loads(captured.out)
    assert cli_summary["query"] == "context summary"
    assert cli_summary["buckets"]["skill"] >= 1
    assert "content" not in cli_summary["sections"][0]


def test_context_pack_applies_bucket_character_limits(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "memory_repo"
    compiler = FolderMemoryCompiler(config=FolderMemoryCompilerConfig(use_memory_service=False))
    compiler.scaffold(output)
    manual_skill = output / "skill" / "manual-skill.md"
    manual_skill.write_text(
        "# Manual Skill Card\n\n" + ("Check generated skill context before use. " * 80),
        encoding="utf-8",
    )

    repo = MarkdownMemoryRepository(output)
    pack = repo.build_context_pack(
        buckets=["skill"],
        max_chars=5000,
        include_generated=False,
        bucket_char_limits={"skill": 500},
    )

    assert pack.bucket_char_limits == {"skill": 500}
    assert pack.used_chars_by_bucket["skill"] <= 500
    assert "[truncated]" in pack.sections[0].content

    assert context_cli_main(
        [
            str(output),
            "--bucket",
            "skill",
            "--no-generated",
            "--bucket-max",
            "skill=500",
            "--format",
            "summary",
        ]
    ) == 0
    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert summary["bucket_char_limits"] == {"skill": 500}
    assert summary["used_chars_by_bucket"]["skill"] <= 500


def test_context_cli_uses_repo_harness_config_defaults(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / "notes.txt").write_text(
        "The user prefers calm answers. Skill: reuse repo harness context defaults. " * 20,
        encoding="utf-8",
    )
    output = tmp_path / "memory_repo"
    folder_cli_main([str(source), str(output)])
    capsys.readouterr()
    (output / ".memu" / "harness.json").write_text(
        json.dumps(
            {
                "version": 1,
                "context": {
                    "buckets": ["skill"],
                    "bucket_char_limits": {"skill": 260},
                    "format": "summary",
                    "max_chars": 900,
                },
            }
        ),
        encoding="utf-8",
    )

    assert context_cli_main([str(output)]) == 0
    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert summary["max_chars"] == 900
    assert summary["bucket_char_limits"] == {"skill": 260}
    assert summary["buckets"]["skill"] >= 1
    assert summary["buckets"]["memory"] == 0
    assert summary["buckets"]["soul"] == 0

    assert context_cli_main(
        [
            str(output),
            "--bucket",
            "memory",
            "--bucket-max",
            "memory=400",
            "--max-chars",
            "1200",
            "--json",
        ]
    ) == 0
    captured = capsys.readouterr()
    pack = json.loads(captured.out)
    assert pack["max_chars"] == 1200
    assert pack["bucket_char_limits"] == {"memory": 400}
    assert all(section["bucket"] == "memory" for section in pack["sections"])


def test_context_pack_exports_system_prompt_and_messages(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / "notes.txt").write_text("Skill: run focused validation after edits.", encoding="utf-8")
    output = tmp_path / "memory_repo"
    folder_cli_main([str(source), str(output)])
    capsys.readouterr()

    repo = MarkdownMemoryRepository(output)
    pack = repo.build_context_pack(query="validation", max_chars=3000)
    messages = pack.to_messages()

    assert messages == [{"role": "system", "content": pack.to_system_prompt()}]
    assert "<memu_context_instructions>" in messages[0]["content"]
    assert "<memu_context>" in messages[0]["content"]
    assert "Prefer manual sections" in messages[0]["content"]

    exit_code = context_cli_main([str(output), "--query", "validation", "--format", "messages"])

    captured = capsys.readouterr()
    cli_messages = json.loads(captured.out)
    assert exit_code == 0
    assert cli_messages[0]["role"] == "system"
    assert "<memu_context_instructions>" in cli_messages[0]["content"]
    assert "run focused validation" in cli_messages[0]["content"]


def test_context_pack_injects_into_chat_messages_without_mutation(
    tmp_path: Path,
) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / "notes.txt").write_text("Skill: inject context without mutating messages.", encoding="utf-8")
    output = tmp_path / "memory_repo"
    compile_folder_to_markdown_sync(
        source,
        output,
        config=FolderMemoryCompilerConfig(use_memory_service=False),
    )

    pack = MarkdownMemoryRepository(output).build_context_pack(query="inject context")
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "What should I do?"},
    ]

    injected = pack.inject_into_messages(messages)

    assert messages[0]["content"] == "You are helpful."
    assert injected is not messages
    assert injected[0]["role"] == "system"
    assert injected[0]["content"].startswith("You are helpful.")
    assert "<memu_context_instructions>" in injected[0]["content"]
    assert "inject context without mutating messages" in injected[0]["content"]

    second = inject_context_messages(injected, pack)
    assert second[0]["content"].count("<memu_context>") == 1
    assert second[0]["content"].count("<memu_context_instructions>") == 1


def test_context_pack_injects_system_message_when_missing(tmp_path: Path) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / "notes.txt").write_text("Skill: create a context system message.", encoding="utf-8")
    output = tmp_path / "memory_repo"
    compile_folder_to_markdown_sync(
        source,
        output,
        config=FolderMemoryCompilerConfig(use_memory_service=False),
    )

    pack = MarkdownMemoryRepository(output).build_context_pack(query="system message")
    messages = [{"role": "user", "content": "Hi"}]

    injected = inject_context_messages(messages, pack)

    assert messages == [{"role": "user", "content": "Hi"}]
    assert injected[0]["role"] == "system"
    assert injected[1]["role"] == "user"
    assert "<memu_context>" in injected[0]["content"]


@pytest.mark.asyncio
async def test_record_skill_trace_feeds_skill_markdown(tmp_path: Path) -> None:
    raw_data = tmp_path / "raw_data"
    output = tmp_path / "memory_repo"
    record = record_skill_trace(
        raw_data,
        task="Fix failing folder compiler tests",
        outcome="success",
        summary="Inspected files, patched code, and ran focused validation.",
        actions=["Read failing test output", "Patch the smallest affected module", "Run focused validation"],
        tools=[SkillToolTrace(name="pytest", success=True, score=0.9)],
        lessons=["Run focused tests after touching compiler behavior."],
    )
    compiler = FolderMemoryCompiler(config=FolderMemoryCompilerConfig(use_memory_service=False))

    await compiler.compile(raw_data, output)

    skill_md = (output / "skill.md").read_text(encoding="utf-8")
    assert record.trace_path.exists()
    assert "Skill Evolution Trace" in record.trace_path.read_text(encoding="utf-8")
    assert "Run focused tests after touching compiler behavior" in skill_md
    assert "skill_traces/" in skill_md


@pytest.mark.asyncio
async def test_context_harness_refreshes_context_and_self_evolves_skills(tmp_path: Path) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / "notes.txt").write_text(
        "The user prefers calm answers. Skill: validate generated context before relying on it.",
        encoding="utf-8",
    )
    output = tmp_path / "memory_repo"
    harness = ContextHarness(
        source,
        output,
        user={"user_id": "u1"},
        compiler_config=FolderMemoryCompilerConfig(use_memory_service=False),
    )

    run = await harness.refresh_context(query="context validation", max_chars=3000)

    assert run.compile_result.processed == ["notes.txt"]
    assert "Skill: validate generated context" in run.context_pack.to_markdown()
    assert (output / "raw_data" / "notes.txt").exists()

    trace_result = await harness.record_skill_trace(
        task="Validate generated context packs",
        outcome="success",
        summary="Compiled raw data and checked the resulting context pack.",
        actions=["Compile raw data", "Build context pack", "Check skill sections"],
        tools=[SkillToolTrace(name="memu-context", success=True, score=0.95)],
        lessons=["Check generated skill sections before injecting context into an agent."],
    )

    assert trace_result.compile_result is not None
    assert any(path.startswith("skill_traces/") for path in trace_result.compile_result.processed)
    assert trace_result.record.trace_path.exists()
    assert "Check generated skill sections" in (output / "skill.md").read_text(encoding="utf-8")
    assert "Check generated skill sections" in harness.build_context_markdown(query="agent context")


def test_context_harness_from_repo_uses_raw_data_and_config_defaults(tmp_path: Path) -> None:
    output = tmp_path / "memory_repo"
    raw_data = output / "raw_data"
    metadata_dir = output / ".memu"
    raw_data.mkdir(parents=True)
    metadata_dir.mkdir()
    (raw_data / "notes.txt").write_text(
        "The user prefers calm answers. Skill: use ContextHarness.from_repo for existing repositories. " * 20,
        encoding="utf-8",
    )
    (raw_data / "debug.tmp").write_text("Temporary output.", encoding="utf-8")
    (metadata_dir / "harness.json").write_text(
        json.dumps(
            {
                "version": 1,
                "compiler": {
                    "exclude_patterns": ["*.tmp"],
                    "max_text_chars": 180,
                },
                "context": {
                    "buckets": ["skill"],
                    "bucket_char_limits": {"skill": 260},
                    "max_chars": 900,
                },
            }
        ),
        encoding="utf-8",
    )

    harness = ContextHarness.from_repo(
        output,
        compiler_config=FolderMemoryCompilerConfig(use_memory_service=False),
    )
    run = harness.refresh_context_sync(query="repo harness")
    manifest = json.loads((output / ".memu" / "manifest.json").read_text(encoding="utf-8"))

    assert harness.source_folder == raw_data.resolve()
    assert run.compile_result.processed == ["notes.txt"]
    assert sorted(manifest["sources"]) == ["notes.txt"]
    assert not (output / "raw_data" / "debug.tmp").exists()
    assert run.context_pack.max_chars == 900
    assert run.context_pack.bucket_char_limits == {"skill": 260}
    assert all(section.bucket == "skill" for section in run.context_pack.sections)

    overridden = harness.build_context_pack(
        buckets=["memory"],
        max_chars=1200,
        bucket_char_limits={},
    )
    assert overridden.max_chars == 1200
    assert overridden.bucket_char_limits == {}
    assert all(section.bucket == "memory" for section in overridden.sections)


def test_context_harness_health_reports_invalid_repo_config(tmp_path: Path) -> None:
    output = tmp_path / "memory_repo"
    raw_data = output / "raw_data"
    metadata_dir = output / ".memu"
    raw_data.mkdir(parents=True)
    metadata_dir.mkdir()
    (raw_data / "notes.txt").write_text("Skill: validate harness config health.", encoding="utf-8")
    (metadata_dir / "harness.json").write_text(
        json.dumps({"version": 1, "context": {"max_chars": 0}}),
        encoding="utf-8",
    )

    harness = ContextHarness.from_repo(output)
    report = harness.health()
    codes = [issue.code for issue in report.issues]

    assert report.ok is False
    assert "invalid_harness_config" in codes
    with pytest.raises(SystemExit):
        harness.refresh_context_sync()


def test_skill_trace_cli_records_and_compiles(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    raw_data = tmp_path / "raw_data"
    output = tmp_path / "memory_repo"

    exit_code = skill_trace_cli_main(
        [
            str(raw_data),
            "--task",
            "Validate generated context packs",
            "--outcome",
            "success",
            "--summary",
            "Generated a context pack and verified skill sections.",
            "--action",
            "Build context pack",
            "--lesson",
            "After compiling raw data, validate the context pack before relying on it.",
            "--tool",
            "memu-context:success:0.95",
            "--metadata",
            "agent_id=codex",
            "--output-folder",
            str(output),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert exit_code == 0
    assert Path(summary["trace_path"]).exists()
    assert summary["compiled"]["entry_count"] >= 1
    assert (output / "skill.md").exists()


def test_context_harness_cli_refresh_outputs_context_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / "notes.txt").write_text(
        "The user prefers calm answers. Skill: validate generated context before relying on it.",
        encoding="utf-8",
    )
    output = tmp_path / "memory_repo"

    exit_code = harness_cli_main(
        [
            "refresh",
            str(source),
            str(output),
            "--query",
            "context validation",
            "--json",
            "--user",
            "user_id=u1",
        ]
    )

    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert exit_code == 0
    assert summary["compile"]["processed"] == ["notes.txt"]
    assert summary["context"]["query"] == "context validation"
    assert any(section["bucket"] == "skill" for section in summary["context"]["sections"])

    assert harness_cli_main(["context", str(output), "--query", "validation", "--json"]) == 0
    captured = capsys.readouterr()
    pack = json.loads(captured.out)
    assert pack["query"] == "validation"
    assert any(section["bucket"] == "skill" for section in pack["sections"])
    assert (output / "raw_data" / "notes.txt").exists()

    assert harness_cli_main(["refresh", str(output), "--query", "validation", "--format", "messages"]) == 0
    captured = capsys.readouterr()
    messages = json.loads(captured.out)
    assert messages[0]["role"] == "system"
    assert "<memu_context_instructions>" in messages[0]["content"]
    assert "Skill: validate generated context" in messages[0]["content"]

    assert harness_cli_main(["refresh", str(output), "--query", "validation", "--format", "summary"]) == 0
    captured = capsys.readouterr()
    refresh_summary = json.loads(captured.out)
    assert refresh_summary["query"] == "validation"
    assert refresh_summary["buckets"]["skill"] >= 1
    assert "compile" not in refresh_summary


def test_context_harness_cli_refresh_writes_json_output_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / "notes.txt").write_text("Skill: write rendered context files for agents.", encoding="utf-8")
    output = tmp_path / "memory_repo"
    context_path = tmp_path / "artifacts" / "refresh.json"

    exit_code = harness_cli_main(
        [
            "refresh",
            str(source),
            str(output),
            "--query",
            "context files",
            "--json",
            "--output",
            str(context_path),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(context_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert captured.out == ""
    assert payload["compile"]["processed"] == ["notes.txt"]
    assert payload["context"]["query"] == "context files"
    assert any(section["bucket"] == "skill" for section in payload["context"]["sections"])


def test_context_harness_cli_json_is_ascii_safe_and_strips_utf8_bom(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    (source / "notes.txt").write_bytes(
        "\ufeffThe user prefers concise Chinese context. "
        "Skill: validate BOM-safe generated context.".encode("utf-8")
    )
    (source / "workflow.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (source / "workflow.caption.md").write_bytes(
        "\ufeffSkill: compare screenshots against acceptance criteria.".encode("utf-8")
    )
    output = tmp_path / "memory_repo"

    exit_code = harness_cli_main(
        [
            "refresh",
            str(source),
            str(output),
            "--query",
            "BOM safe context",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    captured.out.encode("ascii")
    summary = json.loads(captured.out)
    serialized = json.dumps(summary, ensure_ascii=False)
    assert exit_code == 0
    assert "\ufeff" not in serialized
    assert "BOM-safe generated context" in serialized
    assert "compare screenshots against acceptance criteria" in serialized


def test_context_harness_cli_init_scaffolds_memory_repo(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    upload = tmp_path / "upload"
    upload.mkdir()
    (upload / "notes.txt").write_text("Raw note before extraction.", encoding="utf-8")
    media = upload / "media"
    media.mkdir()
    (media / "screenshot.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    output = tmp_path / "memory_repo"

    exit_code = harness_cli_main(
        [
            "init",
            str(output),
            "--source-folder",
            str(upload),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert exit_code == 0
    assert (output / "memory.md").exists()
    assert (output / "AGENTS.md").exists()
    assert (output / "memory").is_dir()
    assert (output / "soul.md").exists()
    assert (output / "soul").is_dir()
    assert (output / "skill.md").exists()
    assert (output / "skill").is_dir()
    assert (output / ".memu" / "manifest.json").exists()
    assert (output / ".memu" / "derived").is_dir()
    assert (output / "raw_data" / "notes.txt").exists()
    assert (output / "raw_data" / "media" / "screenshot.png").exists()
    assert "AGENTS.md" in summary["created"]
    assert sorted(summary["copied"]) == ["media/screenshot.png", "notes.txt"]


def test_context_harness_cli_init_writes_repo_harness_config(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    upload = tmp_path / "upload"
    upload.mkdir()
    (upload / "notes.txt").write_text("Raw note before extraction.", encoding="utf-8")
    (upload / "debug.tmp").write_text("Temporary output.", encoding="utf-8")
    output = tmp_path / "memory_repo"

    exit_code = harness_cli_main(
        [
            "init",
            str(output),
            "--source-folder",
            str(upload),
            "--exclude",
            "*.tmp",
            "--max-text-chars",
            "123",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    config_path = Path(summary["config_path"])
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert config_path == (output / ".memu" / "harness.json").resolve()
    assert config["version"] == 1
    assert config["compiler"]["exclude_patterns"] == ["*.tmp"]
    assert config["compiler"]["max_text_chars"] == 123
    assert config["context"]["format"] == "markdown"
    assert config["context"]["max_chars"] == 8000
    assert (output / "raw_data" / "notes.txt").exists()
    assert not (output / "raw_data" / "debug.tmp").exists()


def test_context_harness_cli_init_preserves_existing_agent_instructions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "memory_repo"
    output.mkdir()
    agents_path = output / "AGENTS.md"
    agents_path.write_text("# Custom agent instructions\n", encoding="utf-8")

    exit_code = harness_cli_main(["init", str(output), "--json"])

    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert exit_code == 0
    assert agents_path.read_text(encoding="utf-8") == "# Custom agent instructions\n"
    assert "AGENTS.md" not in summary["created"]


def test_context_harness_cli_refresh_defaults_to_repo_raw_data(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    upload = tmp_path / "upload"
    upload.mkdir()
    (upload / "notes.txt").write_text(
        "Skill: validate generated context before relying on it.",
        encoding="utf-8",
    )
    output = tmp_path / "memory_repo"

    assert harness_cli_main(["init", str(output), "--source-folder", str(upload), "--json"]) == 0
    capsys.readouterr()

    exit_code = harness_cli_main(["refresh", str(output), "--query", "context validation", "--json"])

    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert exit_code == 0
    assert summary["compile"]["processed"] == ["notes.txt"]
    assert summary["context"]["query"] == "context validation"
    assert any(section["bucket"] == "skill" for section in summary["context"]["sections"])


def test_context_harness_cli_refresh_honors_exclude_patterns(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    upload = tmp_path / "upload"
    upload.mkdir()
    (upload / "notes.txt").write_text("Skill: keep meaningful source files.", encoding="utf-8")
    (upload / "debug.tmp").write_text("Temporary debug output.", encoding="utf-8")
    cache = upload / "node_modules" / "pkg"
    cache.mkdir(parents=True)
    (cache / "cache.txt").write_text("Dependency cache.", encoding="utf-8")
    output = tmp_path / "memory_repo"

    exit_code = harness_cli_main(
        [
            "refresh",
            str(upload),
            str(output),
            "--exclude",
            "node_modules/**",
            "--exclude",
            "*.tmp",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert exit_code == 0
    assert summary["compile"]["processed"] == ["notes.txt"]
    assert not (output / "raw_data" / "debug.tmp").exists()
    assert not (output / "raw_data" / "node_modules").exists()


def test_context_harness_cli_refresh_uses_repo_memuignore(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "memory_repo"
    raw_data = output / "raw_data"
    raw_data.mkdir(parents=True)
    (output / ".memuignore").write_text("node_modules/**\n*.tmp\n", encoding="utf-8")
    (raw_data / "notes.txt").write_text("Skill: keep meaningful source files.", encoding="utf-8")
    (raw_data / "debug.tmp").write_text("Temporary debug output.", encoding="utf-8")
    cache = raw_data / "node_modules" / "pkg"
    cache.mkdir(parents=True)
    (cache / "cache.txt").write_text("Dependency cache.", encoding="utf-8")

    exit_code = harness_cli_main(["refresh", str(output), "--json"])

    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert exit_code == 0
    assert summary["compile"]["processed"] == ["notes.txt"]
    assert not (output / "raw_data" / "debug.tmp").exists()
    assert not (output / "raw_data" / "node_modules").exists()


def test_context_harness_cli_refresh_uses_repo_harness_config_defaults(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "memory_repo"
    raw_data = output / "raw_data"
    metadata_dir = output / ".memu"
    raw_data.mkdir(parents=True)
    metadata_dir.mkdir()
    (raw_data / "notes.txt").write_text(
        "Skill: keep repo harness config defaults available for agent context. " * 20,
        encoding="utf-8",
    )
    (raw_data / "debug.tmp").write_text("Temporary output.", encoding="utf-8")
    (metadata_dir / "harness.json").write_text(
        json.dumps(
            {
                "version": 1,
                "compiler": {
                    "exclude_patterns": ["*.tmp"],
                    "max_text_chars": 160,
                },
                "context": {
                    "buckets": ["skill"],
                    "bucket_char_limits": {"skill": 240},
                    "format": "summary",
                    "max_chars": 900,
                },
            }
        ),
        encoding="utf-8",
    )

    exit_code = harness_cli_main(["refresh", str(output)])

    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    manifest = json.loads((output / ".memu" / "manifest.json").read_text(encoding="utf-8"))
    assert exit_code == 0
    assert summary["max_chars"] == 900
    assert summary["bucket_char_limits"] == {"skill": 240}
    assert summary["buckets"]["skill"] >= 1
    assert summary["buckets"]["memory"] == 0
    assert summary["buckets"]["soul"] == 0
    assert sorted(manifest["sources"]) == ["notes.txt"]
    assert not (output / "raw_data" / "debug.tmp").exists()


def test_context_harness_cli_status_reports_manifest_delta(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    upload = tmp_path / "upload"
    upload.mkdir()
    (upload / "keep.txt").write_text("Durable memory evidence.", encoding="utf-8")
    media = upload / "media"
    media.mkdir()
    (media / "workflow.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (media / "workflow.caption.md").write_text("Skill: inspect screenshots.", encoding="utf-8")
    output = tmp_path / "memory_repo"

    assert harness_cli_main(["init", str(output), "--source-folder", str(upload), "--json"]) == 0
    capsys.readouterr()
    assert harness_cli_main(["refresh", str(output), "--json"]) == 0
    capsys.readouterr()

    (output / "raw_data" / "keep.txt").unlink()
    (output / "raw_data" / "new.txt").write_text("Skill: validate status reports.", encoding="utf-8")
    (output / "raw_data" / "media" / "workflow.caption.md").write_text(
        "Skill: compare screenshots against acceptance criteria.",
        encoding="utf-8",
    )

    exit_code = harness_cli_main(["status", str(output), "--json"])

    captured = capsys.readouterr()
    report = json.loads(captured.out)
    changed_source = next(source for source in report["sources"] if source["path"] == "media/workflow.png")
    assert exit_code == 0
    assert report["new"] == ["new.txt"]
    assert report["changed"] == ["media/workflow.png"]
    assert report["removed"] == ["keep.txt"]
    assert "media/workflow.caption.md" not in report["new"]
    assert changed_source["sidecars"] == ["media/workflow.caption.md"]


def test_context_harness_cli_doctor_reports_repository_health(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    upload = tmp_path / "upload"
    upload.mkdir()
    (upload / "notes.txt").write_text("Skill: validate repository health.", encoding="utf-8")
    output = tmp_path / "memory_repo"

    assert harness_cli_main(["refresh", str(upload), str(output), "--json"]) == 0
    capsys.readouterr()

    assert harness_cli_main(["doctor", str(output), "--json"]) == 0
    captured = capsys.readouterr()
    healthy = json.loads(captured.out)
    assert healthy["ok"] is True
    assert healthy["counts"]["errors"] == 0

    (output / "raw_data" / "notes.txt").unlink()

    exit_code = harness_cli_main(["doctor", str(output), "--json"])

    captured = capsys.readouterr()
    broken = json.loads(captured.out)
    codes = [issue["code"] for issue in broken["issues"]]
    assert exit_code == 1
    assert broken["ok"] is False
    assert "missing_raw_source" in codes


def test_context_harness_cli_doctor_reports_invalid_harness_config(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "memory_repo"
    assert harness_cli_main(["init", str(output), "--json"]) == 0
    capsys.readouterr()

    (output / ".memu" / "harness.json").write_text(
        json.dumps(
            {
                "version": 1,
                "context": {
                    "max_chars": 0,
                },
            }
        ),
        encoding="utf-8",
    )

    exit_code = harness_cli_main(["doctor", str(output), "--json"])

    captured = capsys.readouterr()
    report = json.loads(captured.out)
    codes = [issue["code"] for issue in report["issues"]]
    assert exit_code == 1
    assert report["ok"] is False
    assert "invalid_harness_config" in codes


def test_context_harness_cli_doctor_warns_when_agent_instructions_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    upload = tmp_path / "upload"
    upload.mkdir()
    (upload / "notes.txt").write_text("Skill: validate repository health.", encoding="utf-8")
    output = tmp_path / "memory_repo"

    assert harness_cli_main(["refresh", str(upload), str(output), "--json"]) == 0
    capsys.readouterr()

    (output / "AGENTS.md").unlink()

    exit_code = harness_cli_main(["doctor", str(output), "--json"])

    captured = capsys.readouterr()
    report = json.loads(captured.out)
    codes = [issue["code"] for issue in report["issues"]]
    assert exit_code == 0
    assert report["ok"] is True
    assert report["counts"]["warnings"] == 1
    assert "missing_agent_instructions" in codes


def test_context_harness_cli_doctor_warns_about_orphan_evidence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    upload = tmp_path / "upload"
    upload.mkdir()
    (upload / "notes.txt").write_text("Skill: validate repository health.", encoding="utf-8")
    output = tmp_path / "memory_repo"

    assert harness_cli_main(["refresh", str(upload), str(output), "--json"]) == 0
    capsys.readouterr()

    orphan = output / ".memu" / "derived" / "old.txt.evidence.md"
    orphan.write_text("# Evidence: old.txt\n", encoding="utf-8")

    exit_code = harness_cli_main(["doctor", str(output), "--json"])

    captured = capsys.readouterr()
    report = json.loads(captured.out)
    codes = [issue["code"] for issue in report["issues"]]
    assert exit_code == 0
    assert report["ok"] is True
    assert "orphan_evidence" in codes


def test_context_harness_cli_promotes_manual_skill(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    upload = tmp_path / "upload"
    upload.mkdir()
    (upload / "notes.txt").write_text("Skill: validate context packs.", encoding="utf-8")
    output = tmp_path / "memory_repo"

    assert harness_cli_main(["init", str(output), "--source-folder", str(upload), "--json"]) == 0
    capsys.readouterr()
    assert harness_cli_main(["refresh", str(output), "--json"]) == 0
    capsys.readouterr()

    exit_code = harness_cli_main(
        [
            "promote-skill",
            str(output),
            "--title",
            "Validate Context Packs",
            "--when",
            "Before injecting generated context into an agent.",
            "--action",
            "Build the context pack",
            "--action",
            "Check manual and generated skill sections",
            "--lesson",
            "Always inspect promoted skills before relying on generated context.",
            "--source",
            "skill_traces/validate-context-packs.md",
            "--tag",
            "context",
            "--metadata",
            "agent_id=codex",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    skill_md = (output / "skill.md").read_text(encoding="utf-8")
    card_path = Path(summary["card_path"])
    assert exit_code == 0
    assert summary["title"] == "Validate Context Packs"
    assert card_path.exists()
    assert "## Promoted Skill: Validate Context Packs" in skill_md
    first_card = card_path.read_text(encoding="utf-8")
    assert "Always inspect promoted skills" in first_card
    assert "- source: skill_traces/validate-context-packs.md" in first_card
    assert "- agent_id: codex" in first_card

    assert harness_cli_main(
        [
            "promote-skill",
            str(output),
            "--title",
            "Validate Context Packs",
            "--lesson",
            "Compare generated sections against the current task before use.",
            "--json",
        ]
    ) == 0
    captured = capsys.readouterr()
    second_summary = json.loads(captured.out)
    second_card_path = Path(second_summary["card_path"])
    updated_card = second_card_path.read_text(encoding="utf-8")
    updated_skill_md = (output / "skill.md").read_text(encoding="utf-8")
    assert second_card_path == card_path
    assert updated_skill_md.count("## Promoted Skill: Validate Context Packs") == 1
    assert "Always inspect promoted skills" in updated_card
    assert "Compare generated sections against the current task" in updated_card
    assert "- source: skill_traces/validate-context-packs.md" in updated_card
    assert "- agent_id: codex" in updated_card

    assert harness_cli_main(["refresh", str(output), "--json"]) == 0
    capsys.readouterr()
    assert "Promoted Skill: Validate Context Packs" in (output / "skill.md").read_text(encoding="utf-8")

    assert harness_cli_main(["context", str(output), "--bucket", "skill", "--json"]) == 0
    captured = capsys.readouterr()
    pack = json.loads(captured.out)
    manual_sections = [section for section in pack["sections"] if section["kind"] == "manual"]
    manual_sources = [section["source"] for section in manual_sections]
    assert any("Validate Context Packs" in section["content"] for section in manual_sections)
    assert "skill.md" not in manual_sources
    assert "skill/promoted/validate-context-packs.md" in manual_sources


def test_context_harness_cli_suggests_and_promotes_skills_from_traces(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    output = tmp_path / "memory_repo"
    lesson = "Check generated skill sections before injecting context into an agent."
    record_skill_trace(
        source,
        task="Validate generated context packs",
        outcome="success",
        actions=["Build context pack", "Check skill sections"],
        tools=[SkillToolTrace(name="memu-context", success=True, score=0.95)],
        lessons=[lesson],
    )
    record_skill_trace(
        source,
        task="Review generated agent context",
        outcome="success",
        actions=["Build context pack", "Compare generated sections"],
        tools=[SkillToolTrace(name="memu-harness", success=True, score=0.9)],
        lessons=[lesson],
    )

    exit_code = harness_cli_main(
        [
            "suggest-skills",
            str(source),
            str(output),
            "--min-support",
            "2",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    proposal = summary["proposals"][0]
    assert exit_code == 0
    assert summary["proposal_count"] == 1
    assert summary["promoted_count"] == 0
    assert proposal["title"] == "Check Generated Skill Sections"
    assert proposal["support_count"] == 2
    assert lesson in proposal["lessons"]
    assert len(proposal["sources"]) == 2

    assert harness_cli_main(
        [
            "suggest-skills",
            str(source),
            str(output),
            "--min-support",
            "2",
            "--promote",
            "--json",
        ]
    ) == 0
    captured = capsys.readouterr()
    promoted = json.loads(captured.out)
    card_path = Path(promoted["promotions"][0]["card_path"])
    assert promoted["promoted_count"] == 1
    assert card_path.exists()
    assert "Check Generated Skill Sections" in card_path.read_text(encoding="utf-8")

    assert harness_cli_main(["context", str(source), str(output), "--bucket", "skill", "--json"]) == 0
    captured = capsys.readouterr()
    pack = json.loads(captured.out)
    manual_sections = [section for section in pack["sections"] if section["kind"] == "manual"]
    assert any("Check Generated Skill Sections" in section["content"] for section in manual_sections)


def test_context_harness_cli_trace_recompiles_skill_trace(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "upload"
    source.mkdir()
    output = tmp_path / "memory_repo"

    exit_code = harness_cli_main(
        [
            "trace",
            str(source),
            str(output),
            "--task",
            "Validate generated context packs",
            "--outcome",
            "success",
            "--lesson",
            "Check generated skill sections before injecting context into an agent.",
            "--tool",
            "memu-context:success:0.95",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert exit_code == 0
    assert Path(summary["trace_path"]).exists()
    assert summary["compiled"]["entry_count"] >= 1
    assert any(path.startswith("skill_traces/") for path in summary["compiled"]["processed"])
    assert "Check generated skill sections" in (output / "skill.md").read_text(encoding="utf-8")
