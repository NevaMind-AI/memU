from __future__ import annotations

import asyncio
import fnmatch
import hashlib
import inspect
import json
import shutil
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

from memu.app.self_evolve import (
    EvolutionInstruction,
    EvolutionReviewBundle,
    EvolutionReviewConfig,
    PatchProposal,
    ReviewDecision,
    ReviewStatus,
    SelfEvolveEngine,
    apply_reviewed_proposals,
    write_evolution_audit,
)

if TYPE_CHECKING:
    from memu.app.service import MemoryService


MemoryBucket = Literal["memory", "soul", "skill"]
FolderHealthSeverity = Literal["error", "warning"]
FolderSourceState = Literal["new", "changed", "unchanged", "removed"]
FolderWatchReason = Literal["initial", "changed"]

GENERATED_START = "<!-- memu:generated:start -->"
GENERATED_END = "<!-- memu:generated:end -->"


@dataclass(frozen=True)
class FolderMemoryCompilerConfig:
    """Configuration for compiling a raw data folder into Markdown memory files."""

    raw_data_dir_name: str = "raw_data"
    metadata_dir_name: str = ".memu"
    derived_dir_name: str = "derived"
    agent_instructions_name: str = "AGENTS.md"
    ignore_file_name: str = ".memuignore"
    write_agent_instructions: bool = True
    exclude_patterns: tuple[str, ...] = ()
    max_text_chars: int = 4000
    use_memory_service: bool = True
    self_evolve_enabled: bool = True
    evolution_review: EvolutionReviewConfig = field(default_factory=EvolutionReviewConfig)


@dataclass(frozen=True)
class MarkdownMemoryEntry:
    """A generated memory/soul/skill entry ready to be written as Markdown."""

    id: str
    bucket: MemoryBucket
    title: str
    body: str
    source: str
    evidence: str
    modality: str
    confidence: str = "medium"
    tags: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: _utc_now())

    def to_manifest(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "bucket": self.bucket,
            "title": self.title,
            "body": self.body,
            "source": self.source,
            "evidence": self.evidence,
            "modality": self.modality,
            "confidence": self.confidence,
            "tags": list(self.tags),
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_manifest(cls, data: Mapping[str, Any]) -> MarkdownMemoryEntry:
        return cls(
            id=str(data["id"]),
            bucket=cast(MemoryBucket, data["bucket"]),
            title=str(data["title"]),
            body=str(data["body"]),
            source=str(data["source"]),
            evidence=str(data["evidence"]),
            modality=str(data["modality"]),
            confidence=str(data.get("confidence", "medium")),
            tags=[str(tag) for tag in data.get("tags", [])],
            updated_at=str(data.get("updated_at") or _utc_now()),
        )

    def to_markdown(self) -> str:
        tags = ", ".join(self.tags) if self.tags else "generated"
        return (
            f"### {self.id}: {self.title}\n\n"
            f"- bucket: {self.bucket}\n"
            f"- modality: {self.modality}\n"
            f"- confidence: {self.confidence}\n"
            f"- source: {self.source}\n"
            f"- evidence: {self.evidence}\n"
            f"- tags: {tags}\n"
            f"- updated_at: {self.updated_at}\n\n"
            f"{self.body.strip()}\n"
        )


@dataclass(frozen=True)
class FolderCompileResult:
    """Result returned by FolderMemoryCompiler.compile."""

    output_dir: Path
    raw_data_dir: Path
    manifest_path: Path
    processed: list[str]
    skipped: list[str]
    removed: list[str]
    entries: list[MarkdownMemoryEntry]
    evolution_instructions: list[EvolutionInstruction] = field(default_factory=list)
    patch_proposals: list[PatchProposal] = field(default_factory=list)
    review_decisions: list[ReviewDecision] = field(default_factory=list)


@dataclass(frozen=True)
class EvolutionReviewApplyResult:
    """Result returned after creator review decisions are applied to pending proposals."""

    output_dir: Path
    manifest_path: Path
    reviewed: list[ReviewDecision]
    applied_proposal_ids: list[str]
    removed: list[str]
    entries: list[MarkdownMemoryEntry]


@dataclass(frozen=True)
class FolderScaffoldResult:
    """Result returned when a Markdown memory repository layout is scaffolded."""

    output_dir: Path
    raw_data_dir: Path
    manifest_path: Path
    created: list[str]
    copied: list[str]


@dataclass(frozen=True)
class FolderSourceStatus:
    """Status of one source file compared with the latest manifest."""

    path: str
    state: FolderSourceState
    modality: str | None = None
    sha256: str | None = None
    previous_sha256: str | None = None
    raw_path: str | None = None
    evidence: str | None = None
    sidecars: list[str] = field(default_factory=list)
    entry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "state": self.state,
            "modality": self.modality,
            "sha256": self.sha256,
            "previous_sha256": self.previous_sha256,
            "raw_path": self.raw_path,
            "evidence": self.evidence,
            "sidecars": list(self.sidecars),
            "entry_count": self.entry_count,
        }


@dataclass(frozen=True)
class FolderStatusResult:
    """Non-mutating status report for a Markdown memory repository."""

    source_dir: Path
    output_dir: Path
    manifest_path: Path
    sources: list[FolderSourceStatus]

    @property
    def new(self) -> list[str]:
        return self._paths_for("new")

    @property
    def changed(self) -> list[str]:
        return self._paths_for("changed")

    @property
    def unchanged(self) -> list[str]:
        return self._paths_for("unchanged")

    @property
    def removed(self) -> list[str]:
        return self._paths_for("removed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_dir": str(self.source_dir),
            "output_dir": str(self.output_dir),
            "manifest_path": str(self.manifest_path),
            "counts": {
                "new": len(self.new),
                "changed": len(self.changed),
                "unchanged": len(self.unchanged),
                "removed": len(self.removed),
            },
            "new": self.new,
            "changed": self.changed,
            "unchanged": self.unchanged,
            "removed": self.removed,
            "sources": [source.to_dict() for source in self.sources],
        }

    def _paths_for(self, state: FolderSourceState) -> list[str]:
        return [source.path for source in self.sources if source.state == state]


@dataclass(frozen=True)
class FolderHealthIssue:
    """One validation issue found in a Markdown memory repository."""

    severity: FolderHealthSeverity
    code: str
    message: str
    path: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class FolderHealthResult:
    """Non-mutating health report for a Markdown memory repository."""

    output_dir: Path
    issues: list[FolderHealthIssue]

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_dir": str(self.output_dir),
            "ok": self.ok,
            "counts": {
                "errors": self.error_count,
                "warnings": self.warning_count,
            },
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True)
class FolderWatchEvent:
    """A compile event emitted by the folder watcher."""

    iteration: int
    reason: FolderWatchReason
    result: FolderCompileResult
    status: FolderStatusResult | None = None


@dataclass(frozen=True)
class _SourceSnapshot:
    absolute_path: Path
    rel_path: str
    sha256: str
    size: int
    modality: str
    raw_rel_path: str
    evidence_rel_path: str
    sidecar_paths: tuple[Path, ...] = ()
    sidecar_rel_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class _ServiceExtraction:
    entries: list[MarkdownMemoryEntry]
    evidence_text: str


@dataclass(frozen=True)
class _SourceExtraction:
    entries: list[MarkdownMemoryEntry]
    instructions: list[EvolutionInstruction]
    proposals: list[PatchProposal]
    reviews: list[ReviewDecision]


class FolderMemoryCompiler:
    """Compile a folder of multimodal raw data into memory.md, soul.md, and skill.md.

    The compiler is intentionally Markdown-backed: raw files are copied into raw_data/,
    derived textual evidence is cached in .memu/derived/, and generated memory entries
    are written into stable generated blocks so human edits outside the block survive
    subsequent compiles.
    """

    def __init__(
        self,
        memory_service: MemoryService | None = None,
        config: FolderMemoryCompilerConfig | None = None,
    ) -> None:
        self.memory_service = memory_service
        self.config = config or FolderMemoryCompilerConfig()
        self.self_evolve = SelfEvolveEngine(self.config.evolution_review)

    def scaffold(
        self,
        output_folder: str | Path,
        *,
        source_folder: str | Path | None = None,
    ) -> FolderScaffoldResult:
        """Create the Markdown memory repository layout without extracting memories."""

        output_root = Path(output_folder).resolve()
        created: list[str] = []
        paths = self._ensure_scaffold_layout(output_root, created)
        self._write_scaffold_markdown_files(output_root, created)
        self._write_agent_instructions(output_root, created)
        self._write_scaffold_manifest(paths["manifest"], output_root, created)
        copied = self._copy_scaffold_source(source_folder, paths["raw_data"], output_root) if source_folder else []
        return FolderScaffoldResult(
            output_dir=output_root,
            raw_data_dir=paths["raw_data"],
            manifest_path=paths["manifest"],
            created=created,
            copied=copied,
        )

    def status(
        self,
        source_folder: str | Path,
        output_folder: str | Path,
    ) -> FolderStatusResult:
        """Inspect source changes against the manifest without writing files."""

        source_root = Path(source_folder).resolve()
        output_root = Path(output_folder).resolve()
        if not source_root.exists() or not source_root.is_dir():
            msg = f"source_folder must be an existing directory: {source_root}"
            raise ValueError(msg)
        source_root = self._resolve_source_root(source_root, output_root)

        manifest_path = output_root / self.config.metadata_dir_name / "manifest.json"
        manifest = self._load_manifest(manifest_path)
        old_sources = cast(dict[str, Any], manifest.get("sources", {}))
        snapshots = self._scan_sources(source_root, output_root)
        current_rel_paths = {snapshot.rel_path for snapshot in snapshots}
        statuses = [self._status_from_snapshot(snapshot, old_sources.get(snapshot.rel_path)) for snapshot in snapshots]

        for rel_path in sorted(set(old_sources) - current_rel_paths):
            previous = old_sources.get(rel_path)
            if isinstance(previous, Mapping):
                statuses.append(self._removed_status(rel_path, previous))
            else:
                statuses.append(FolderSourceStatus(path=rel_path, state="removed"))

        return FolderStatusResult(
            source_dir=source_root,
            output_dir=output_root,
            manifest_path=manifest_path,
            sources=sorted(statuses, key=lambda source: (self._status_sort_key(source.state), source.path)),
        )

    def health(self, output_folder: str | Path) -> FolderHealthResult:
        """Validate a Markdown memory repository without writing files."""

        output_root = Path(output_folder).resolve()
        issues: list[FolderHealthIssue] = []
        self._check_layout(output_root, issues)
        manifest = self._read_manifest_for_health(output_root, issues)
        if manifest is not None:
            self._check_manifest_sources(output_root, manifest, issues)
            self._check_orphan_evidence(output_root, manifest, issues)
        self._check_generated_blocks(output_root, issues)
        return FolderHealthResult(output_dir=output_root, issues=issues)

    async def compile(
        self,
        source_folder: str | Path,
        output_folder: str | Path,
        *,
        user: Mapping[str, Any] | None = None,
    ) -> FolderCompileResult:
        source_root = Path(source_folder).resolve()
        output_root = Path(output_folder).resolve()
        if not source_root.exists() or not source_root.is_dir():
            msg = f"source_folder must be an existing directory: {source_root}"
            raise ValueError(msg)

        paths = self._ensure_output_layout(output_root)
        created: list[str] = []
        self._write_agent_instructions(output_root, created)
        source_root = self._resolve_source_root(source_root, output_root)
        manifest = self._load_manifest(paths["manifest"])
        old_sources = cast(dict[str, Any], manifest.get("sources", {}))
        snapshots = self._scan_sources(source_root, output_root)
        current_rel_paths = {snapshot.rel_path for snapshot in snapshots}
        processed: list[str] = []
        skipped: list[str] = []
        evolution_instructions: list[EvolutionInstruction] = []
        patch_proposals: list[PatchProposal] = []
        review_decisions: list[ReviewDecision] = []

        for snapshot in snapshots:
            previous = old_sources.get(snapshot.rel_path)
            unchanged = isinstance(previous, Mapping) and previous.get("sha256") == snapshot.sha256
            self._sync_raw_file(snapshot, paths["raw_data"])
            if unchanged and previous.get("entries"):
                skipped.append(snapshot.rel_path)
                continue
            extraction = await self._extract_entries(snapshot, output_root, previous=previous, user=user)
            evolution_instructions.extend(extraction.instructions)
            patch_proposals.extend(extraction.proposals)
            review_decisions.extend(extraction.reviews)
            old_sources[snapshot.rel_path] = {
                "path": snapshot.rel_path,
                "raw_path": snapshot.raw_rel_path,
                "hash": snapshot.sha256,
                "sha256": snapshot.sha256,
                "size": snapshot.size,
                "modality": snapshot.modality,
                "evidence": snapshot.evidence_rel_path,
                "sidecars": list(snapshot.sidecar_rel_paths),
                "entries": [entry.to_manifest() for entry in extraction.entries],
                "evolution": {
                    "instructions": [instruction.to_dict() for instruction in extraction.instructions],
                    "patch_proposals": [proposal.to_dict() for proposal in extraction.proposals],
                    "review_decisions": [review.to_dict() for review in extraction.reviews],
                },
                "last_extracted_at": _utc_now(),
            }
            processed.append(snapshot.rel_path)

        removed = sorted(set(old_sources) - current_rel_paths)
        for rel_path in removed:
            previous = old_sources.get(rel_path)
            if self.config.self_evolve_enabled and isinstance(previous, Mapping):
                bundle = self._evolve_removed_source(rel_path, previous)
                evolution_instructions.extend(bundle.instructions)
                patch_proposals.extend(bundle.proposals)
                review_decisions.extend(bundle.reviews)
                previous_entries = self._source_entries_from_manifest(previous)
                remaining_entries = [
                    MarkdownMemoryEntry.from_manifest(entry)
                    for entry in apply_reviewed_proposals(
                        [entry.to_manifest() for entry in previous_entries],
                        bundle.proposals,
                        bundle.reviews,
                    )
                ]
                if remaining_entries:
                    updated = dict(previous)
                    updated["entries"] = [entry.to_manifest() for entry in remaining_entries]
                    updated["pending_removal"] = True
                    updated["removed_from_source_at"] = _utc_now()
                    updated["evolution"] = bundle.to_dict()
                    old_sources[rel_path] = updated
                    continue
            old_sources.pop(rel_path, None)

        manifest["version"] = 1
        manifest["updated_at"] = _utc_now()
        manifest["sources"] = {key: old_sources[key] for key in sorted(old_sources)}
        self._write_manifest(paths["manifest"], manifest)
        self._remove_stale_raw_files(paths["raw_data"], self._expected_raw_rel_paths_from_sources(manifest["sources"]))
        self._remove_stale_evidence_files(
            paths["derived"],
            self._expected_evidence_rel_paths_from_sources(manifest["sources"]),
        )
        write_evolution_audit(
            paths["metadata"],
            instructions=evolution_instructions,
            proposals=patch_proposals,
            reviews=review_decisions,
        )

        entries = self._entries_from_manifest(manifest)
        self._write_markdown_repository(output_root, entries)

        return FolderCompileResult(
            output_dir=output_root,
            raw_data_dir=paths["raw_data"],
            manifest_path=paths["manifest"],
            processed=processed,
            skipped=skipped,
            removed=removed,
            entries=entries,
            evolution_instructions=evolution_instructions,
            patch_proposals=patch_proposals,
            review_decisions=review_decisions,
        )

    def review_evolution(
        self,
        output_folder: str | Path,
        *,
        proposal_ids: Sequence[str] | None = None,
        reviewer: str = "creator",
        decision: ReviewStatus = "approved",
        reason: str = "",
    ) -> EvolutionReviewApplyResult:
        """Apply creator review decisions to pending self-evolve patch proposals."""

        if decision not in {"approved", "rejected"}:
            msg = "decision must be 'approved' or 'rejected'"
            raise ValueError(msg)
        output_root = Path(output_folder).resolve()
        manifest_path = output_root / self.config.metadata_dir_name / "manifest.json"
        manifest = self._load_manifest(manifest_path)
        sources = cast(dict[str, Any], manifest.get("sources", {}))
        selected_ids = {proposal_id for proposal_id in proposal_ids or [] if proposal_id}
        reviewed: list[ReviewDecision] = []
        applied_proposal_ids: list[str] = []
        removed: list[str] = []

        for rel_path, source in list(sources.items()):
            if not isinstance(source, Mapping):
                continue
            evolution = source.get("evolution", {})
            if not isinstance(evolution, Mapping):
                continue
            proposals = [
                PatchProposal.from_dict(proposal)
                for proposal in evolution.get("patch_proposals", [])
                if isinstance(proposal, Mapping)
            ]
            if not proposals:
                continue
            reviews = [
                ReviewDecision.from_dict(review)
                for review in evolution.get("review_decisions", [])
                if isinstance(review, Mapping)
            ]
            latest_reviews = {review.proposal_id: review for review in reviews}
            new_reviews: list[ReviewDecision] = []
            for proposal in proposals:
                if selected_ids and proposal.id not in selected_ids:
                    continue
                latest = latest_reviews.get(proposal.id)
                if latest is None or latest.status != "needs_review":
                    continue
                review = ReviewDecision(
                    proposal_id=proposal.id,
                    status=decision,
                    reviewer=reviewer,
                    reason=reason or f"Creator marked proposal as {decision}.",
                    confidence=proposal.confidence,
                    safety_flags=list(latest.safety_flags),
                )
                new_reviews.append(review)
                reviewed.append(review)
                if decision == "approved":
                    applied_proposal_ids.append(proposal.id)

            if not new_reviews:
                continue
            combined_reviews = [*reviews, *new_reviews]
            updated_source = dict(source)
            updated_evolution = dict(evolution)
            updated_evolution["review_decisions"] = [review.to_dict() for review in combined_reviews]
            updated_source["evolution"] = updated_evolution
            updated_entries = apply_reviewed_proposals(
                self._entry_manifests_from_source(source),
                proposals,
                combined_reviews,
            )
            updated_source["entries"] = updated_entries
            if updated_source.get("pending_removal") and not updated_entries:
                removed.append(str(rel_path))
                sources.pop(rel_path, None)
            else:
                sources[rel_path] = updated_source

        manifest["version"] = 1
        manifest["updated_at"] = _utc_now()
        manifest["sources"] = {key: sources[key] for key in sorted(sources)}
        self._write_manifest(manifest_path, manifest)
        paths = self._ensure_output_layout(output_root)
        self._remove_stale_raw_files(paths["raw_data"], self._expected_raw_rel_paths_from_sources(manifest["sources"]))
        self._remove_stale_evidence_files(
            paths["derived"],
            self._expected_evidence_rel_paths_from_sources(manifest["sources"]),
        )
        write_evolution_audit(paths["metadata"], instructions=[], proposals=[], reviews=reviewed)
        entries = self._entries_from_manifest(manifest)
        self._write_markdown_repository(output_root, entries)
        return EvolutionReviewApplyResult(
            output_dir=output_root,
            manifest_path=manifest_path,
            reviewed=reviewed,
            applied_proposal_ids=applied_proposal_ids,
            removed=removed,
            entries=entries,
        )

    def _ensure_output_layout(self, output_root: Path) -> dict[str, Path]:
        raw_data_dir = output_root / self.config.raw_data_dir_name
        metadata_dir = output_root / self.config.metadata_dir_name
        derived_dir = metadata_dir / self.config.derived_dir_name
        manifest_path = metadata_dir / "manifest.json"
        for path in (
            output_root,
            raw_data_dir,
            metadata_dir,
            derived_dir,
            output_root / "memory",
            output_root / "soul",
            output_root / "skill",
        ):
            path.mkdir(parents=True, exist_ok=True)
        return {
            "raw_data": raw_data_dir,
            "metadata": metadata_dir,
            "derived": derived_dir,
            "manifest": manifest_path,
        }

    def _check_layout(self, output_root: Path, issues: list[FolderHealthIssue]) -> None:
        required_dirs = [
            self.config.raw_data_dir_name,
            self.config.metadata_dir_name,
            f"{self.config.metadata_dir_name}/{self.config.derived_dir_name}",
            "memory",
            "soul",
            "skill",
        ]
        required_files = [
            "memory.md",
            "soul.md",
            "skill.md",
            f"{self.config.metadata_dir_name}/manifest.json",
        ]
        if not output_root.exists():
            self._health_issue(issues, "error", "missing_output_dir", "Repository directory is missing.", ".")
            return
        if not output_root.is_dir():
            self._health_issue(issues, "error", "output_not_directory", "Repository path is not a directory.", ".")
            return
        for rel_path in required_dirs:
            path = output_root / rel_path
            if not path.is_dir():
                self._health_issue(issues, "error", "missing_directory", "Required directory is missing.", rel_path)
        for rel_path in required_files:
            path = output_root / rel_path
            if not path.is_file():
                self._health_issue(issues, "error", "missing_file", "Required file is missing.", rel_path)
        if self.config.write_agent_instructions:
            instructions_path = output_root / self.config.agent_instructions_name
            if not instructions_path.is_file():
                self._health_issue(
                    issues,
                    "warning",
                    "missing_agent_instructions",
                    "Agent bootstrap instructions are missing.",
                    self.config.agent_instructions_name,
                )

    def _read_manifest_for_health(
        self,
        output_root: Path,
        issues: list[FolderHealthIssue],
    ) -> dict[str, Any] | None:
        manifest_path = output_root / self.config.metadata_dir_name / "manifest.json"
        if not manifest_path.exists():
            return None
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            self._health_issue(
                issues,
                "error",
                "invalid_manifest_json",
                "Manifest is not valid JSON.",
                _relative_to(manifest_path, output_root),
                {"error": str(exc)},
            )
            return None
        if not isinstance(manifest, dict):
            self._health_issue(
                issues,
                "error",
                "invalid_manifest_shape",
                "Manifest root must be a JSON object.",
                _relative_to(manifest_path, output_root),
            )
            return None
        sources = manifest.get("sources", {})
        if not isinstance(sources, Mapping):
            self._health_issue(
                issues,
                "error",
                "invalid_manifest_sources",
                "Manifest sources must be an object.",
                _relative_to(manifest_path, output_root),
            )
            return None
        return manifest

    def _check_manifest_sources(
        self,
        output_root: Path,
        manifest: Mapping[str, Any],
        issues: list[FolderHealthIssue],
    ) -> None:
        sources = manifest.get("sources", {})
        if not isinstance(sources, Mapping):
            return
        for key, source in sources.items():
            if not isinstance(source, Mapping):
                self._health_issue(
                    issues,
                    "error",
                    "invalid_source_record",
                    "Manifest source record must be an object.",
                    str(key),
                )
                continue
            source_path = str(source.get("path") or key)
            raw_path = str(source.get("raw_path") or f"{self.config.raw_data_dir_name}/{source_path}")
            evidence_path = str(source.get("evidence") or "")
            if not (output_root / raw_path).is_file():
                self._health_issue(issues, "error", "missing_raw_source", "Raw source file is missing.", raw_path)
            if evidence_path and not (output_root / evidence_path).is_file():
                self._health_issue(
                    issues,
                    "warning",
                    "missing_evidence",
                    "Derived evidence file is missing.",
                    evidence_path,
                    {"source": source_path},
                )
            for sidecar in source.get("sidecars", []):
                sidecar_path = f"{self.config.raw_data_dir_name}/{sidecar}"
                if not (output_root / sidecar_path).is_file():
                    self._health_issue(
                        issues,
                        "warning",
                        "missing_sidecar",
                        "Raw sidecar file is missing.",
                        sidecar_path,
                        {"source": source_path},
                    )
            entries = source.get("entries", [])
            if not isinstance(entries, list) or not entries:
                self._health_issue(
                    issues,
                    "warning",
                    "source_without_entries",
                    "Manifest source has no generated entries.",
                    source_path,
                )
                continue
            self._check_manifest_entries(output_root, source_path, entries, issues)

    def _check_orphan_evidence(
        self,
        output_root: Path,
        manifest: Mapping[str, Any],
        issues: list[FolderHealthIssue],
    ) -> None:
        derived_dir = output_root / self.config.metadata_dir_name / self.config.derived_dir_name
        if not derived_dir.is_dir():
            return
        sources = manifest.get("sources", {})
        if not isinstance(sources, Mapping):
            return
        expected = {
            str(source.get("evidence"))
            for source in sources.values()
            if isinstance(source, Mapping) and source.get("evidence")
        }
        for path in sorted(derived_dir.rglob("*.evidence.md")):
            rel_path = _relative_to(path, output_root)
            if rel_path not in expected:
                self._health_issue(
                    issues,
                    "warning",
                    "orphan_evidence",
                    "Derived evidence file is not referenced by the manifest.",
                    rel_path,
                )

    def _check_manifest_entries(
        self,
        output_root: Path,
        source_path: str,
        entries: Sequence[Any],
        issues: list[FolderHealthIssue],
    ) -> None:
        for entry in entries:
            if not isinstance(entry, Mapping):
                self._health_issue(
                    issues,
                    "error",
                    "invalid_entry_record",
                    "Manifest entry must be an object.",
                    source_path,
                )
                continue
            bucket = str(entry.get("bucket", ""))
            entry_id = str(entry.get("id", ""))
            if bucket not in {"memory", "soul", "skill"}:
                self._health_issue(
                    issues,
                    "error",
                    "invalid_entry_bucket",
                    "Manifest entry has an invalid bucket.",
                    source_path,
                    {"entry_id": entry_id, "bucket": bucket},
                )
                continue
            detail_path = output_root / bucket / f"{_safe_markdown_name(str(entry.get('source', source_path)))}.md"
            if not detail_path.is_file():
                self._health_issue(
                    issues,
                    "warning",
                    "missing_detail_file",
                    "Per-source detail Markdown file is missing.",
                    _relative_to(detail_path, output_root),
                    {"entry_id": entry_id},
                )

    def _check_generated_blocks(self, output_root: Path, issues: list[FolderHealthIssue]) -> None:
        for rel_path in ("memory.md", "soul.md", "skill.md"):
            self._check_generated_block_file(output_root, rel_path, issues, required=True)
        for bucket in ("memory", "soul", "skill"):
            bucket_dir = output_root / bucket
            if not bucket_dir.is_dir():
                continue
            for path in sorted(bucket_dir.rglob("*.md")):
                self._check_generated_block_file(output_root, _relative_to(path, output_root), issues, required=False)

    def _check_generated_block_file(
        self,
        output_root: Path,
        rel_path: str,
        issues: list[FolderHealthIssue],
        *,
        required: bool,
    ) -> None:
        path = output_root / rel_path
        if not path.exists():
            return
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            self._health_issue(issues, "warning", "markdown_decode_error", "Markdown file is not UTF-8.", rel_path)
            return
        has_start = GENERATED_START in text
        has_end = GENERATED_END in text
        if has_start != has_end:
            self._health_issue(
                issues,
                "error",
                "unbalanced_generated_block",
                "Generated block markers are unbalanced.",
                rel_path,
            )
        elif required and not has_start:
            self._health_issue(
                issues,
                "error",
                "missing_generated_block",
                "Required top-level Markdown file has no generated block.",
                rel_path,
            )

    def _health_issue(
        self,
        issues: list[FolderHealthIssue],
        severity: FolderHealthSeverity,
        code: str,
        message: str,
        path: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        issues.append(
            FolderHealthIssue(
                severity=severity,
                code=code,
                message=message,
                path=path,
                details=dict(details or {}),
            )
        )

    def _ensure_scaffold_layout(self, output_root: Path, created: list[str]) -> dict[str, Path]:
        raw_data_dir = output_root / self.config.raw_data_dir_name
        metadata_dir = output_root / self.config.metadata_dir_name
        derived_dir = metadata_dir / self.config.derived_dir_name
        manifest_path = metadata_dir / "manifest.json"
        for path in (
            output_root,
            raw_data_dir,
            metadata_dir,
            derived_dir,
            output_root / "memory",
            output_root / "soul",
            output_root / "skill",
        ):
            self._mkdir_if_missing(path, output_root, created)
        return {
            "raw_data": raw_data_dir,
            "metadata": metadata_dir,
            "derived": derived_dir,
            "manifest": manifest_path,
        }

    def _mkdir_if_missing(self, path: Path, output_root: Path, created: list[str]) -> None:
        if not path.exists():
            created.append(_relative_to(path, output_root))
        path.mkdir(parents=True, exist_ok=True)

    def _write_scaffold_markdown_files(self, output_root: Path, created: list[str]) -> None:
        for bucket, title in (("memory", "Memory"), ("soul", "Soul"), ("skill", "Skill")):
            self._write_scaffold_file(output_root / f"{bucket}.md", output_root, title, created)

    def _write_agent_instructions(self, output_root: Path, created: list[str]) -> None:
        if not self.config.write_agent_instructions:
            return
        target = output_root / self.config.agent_instructions_name
        if target.exists():
            return
        raw_data_dir = self.config.raw_data_dir_name
        target.write_text(
            "\n".join(
                [
                    "# AGENTS.md",
                    "",
                    "Guidance for agents using this memU context harness repository.",
                    "",
                    "## Context Harness",
                    "",
                    "- Treat this folder as a Markdown-backed memory repository.",
                    "- Read `memory.md` for durable facts, events, and project context.",
                    "- Read `soul.md` for persona, tone, style, and preference signals.",
                    "- Read `skill.md` for reusable procedures, tool patterns, and lessons.",
                    "- Generated blocks are managed by memU. Put manual notes outside those blocks.",
                    f"- Raw evidence lives in `{raw_data_dir}/`; preserve original files when possible.",
                    "- Do not let raw logs or feedback rewrite long-term context directly; route them through "
                    "Evolution Instructions, Patch Proposals, and the review gate.",
                    "- Add sidecars beside multimodal files when semantic evidence is needed.",
                    "- Use `.memuignore` or `--exclude` for noisy caches, build outputs, or temporary files.",
                    "- Record task traces before promoting durable skills.",
                    "",
                    "## Useful Commands",
                    "",
                    "```bash",
                    "memu-harness doctor .",
                    "memu-harness status .",
                    "memu-harness refresh . --exclude \"node_modules/**\"",
                    "memu-harness refresh .  # also honors .memuignore",
                    "memu-harness refresh . --query \"current task\"",
                    "memu-harness context . --query \"current task\" --format system",
                    "memu-harness context . --format system --output context.system.md",
                    "memu-harness context . --bucket-max soul=1000 --bucket-max skill=2000",
                    "memu-harness trace . --task \"What changed?\" --outcome success",
                    "memu-harness suggest-skills .",
                    "memu-harness promote-skill . --title \"Reusable workflow\"",
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        created.append(_relative_to(target, output_root))

    def _write_scaffold_file(self, target: Path, output_root: Path, title: str, created: list[str]) -> None:
        if target.exists():
            return
        target.write_text(
            f"# {title}\n\n{GENERATED_START}\nNo generated entries yet.\n{GENERATED_END}\n\n",
            encoding="utf-8",
        )
        created.append(_relative_to(target, output_root))

    def _write_scaffold_manifest(self, manifest_path: Path, output_root: Path, created: list[str]) -> None:
        if manifest_path.exists():
            return
        manifest = {"version": 1, "updated_at": _utc_now(), "sources": {}}
        self._write_manifest(manifest_path, manifest)
        created.append(_relative_to(manifest_path, output_root))

    def _copy_scaffold_source(
        self,
        source_folder: str | Path,
        raw_data_dir: Path,
        output_root: Path,
    ) -> list[str]:
        source_root = Path(source_folder).resolve()
        if not source_root.exists() or not source_root.is_dir():
            msg = f"source_folder must be an existing directory: {source_root}"
            raise ValueError(msg)
        if source_root == output_root:
            msg = "source_folder must not be the same as output_folder when scaffolding raw_data"
            raise ValueError(msg)

        exclude_patterns = self._effective_exclude_patterns(source_root, output_root)
        copied: list[str] = []
        for path in sorted(source_root.rglob("*")):
            if not path.is_file() or self._is_output_tree_path(path, source_root, output_root):
                continue
            if self._is_excluded_source_path(path, source_root, exclude_patterns):
                continue
            rel_path = path.relative_to(source_root)
            destination = raw_data_dir / rel_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            if path.resolve() == destination.resolve():
                continue
            shutil.copy2(path, destination)
            copied.append(_to_posix(rel_path))
        return copied

    def _scan_sources(self, source_root: Path, output_root: Path) -> list[_SourceSnapshot]:
        snapshots: list[_SourceSnapshot] = []
        exclude_patterns = self._effective_exclude_patterns(source_root, output_root)
        source_files = {
            path
            for path in source_root.rglob("*")
            if path.is_file() and not self._is_generated_path(path, source_root, output_root)
            and not self._is_excluded_source_path(path, source_root, exclude_patterns)
        }
        for path in sorted(source_files):
            if self._is_paired_sidecar(path, source_files):
                continue
            rel_path = _to_posix(path.relative_to(source_root))
            modality = self._detect_modality(path)
            sidecar_paths = (
                tuple(self._find_sidecar_files(path, source_root, exclude_patterns))
                if self._supports_sidecars(modality)
                else ()
            )
            sidecar_rel_paths = tuple(_to_posix(sidecar.relative_to(source_root)) for sidecar in sidecar_paths)
            sha256 = self._hash_source(path, sidecar_paths)
            raw_rel_path = f"{self.config.raw_data_dir_name}/{rel_path}"
            evidence_rel_path = f"{self.config.metadata_dir_name}/{self.config.derived_dir_name}/{rel_path}.evidence.md"
            snapshots.append(
                _SourceSnapshot(
                    absolute_path=path,
                    rel_path=rel_path,
                    sha256=sha256,
                    size=path.stat().st_size,
                    modality=modality,
                    raw_rel_path=raw_rel_path,
                    evidence_rel_path=evidence_rel_path,
                    sidecar_paths=sidecar_paths,
                    sidecar_rel_paths=sidecar_rel_paths,
                )
            )
        return snapshots

    def _status_from_snapshot(
        self,
        snapshot: _SourceSnapshot,
        previous: Any,
    ) -> FolderSourceStatus:
        previous_sha = str(previous.get("sha256", "")) if isinstance(previous, Mapping) else None
        previous_entries = previous.get("entries", []) if isinstance(previous, Mapping) else []
        if not isinstance(previous, Mapping):
            state: FolderSourceState = "new"
        elif previous_sha == snapshot.sha256 and previous_entries:
            state = "unchanged"
        else:
            state = "changed"
        return FolderSourceStatus(
            path=snapshot.rel_path,
            state=state,
            modality=snapshot.modality,
            sha256=snapshot.sha256,
            previous_sha256=previous_sha,
            raw_path=snapshot.raw_rel_path,
            evidence=snapshot.evidence_rel_path,
            sidecars=list(snapshot.sidecar_rel_paths),
            entry_count=len(previous_entries) if isinstance(previous_entries, list) else 0,
        )

    def _removed_status(self, rel_path: str, previous: Mapping[str, Any]) -> FolderSourceStatus:
        entries = previous.get("entries", [])
        return FolderSourceStatus(
            path=rel_path,
            state="removed",
            modality=str(previous.get("modality")) if previous.get("modality") else None,
            sha256=None,
            previous_sha256=str(previous.get("sha256")) if previous.get("sha256") else None,
            raw_path=str(previous.get("raw_path")) if previous.get("raw_path") else None,
            evidence=str(previous.get("evidence")) if previous.get("evidence") else None,
            sidecars=[str(sidecar) for sidecar in previous.get("sidecars", [])],
            entry_count=len(entries) if isinstance(entries, list) else 0,
        )

    def _status_sort_key(self, state: FolderSourceState) -> int:
        return {"new": 0, "changed": 1, "removed": 2, "unchanged": 3}[state]

    def source_fingerprint(self, source_folder: str | Path, output_folder: str | Path) -> tuple[tuple[str, str], ...]:
        source_root = Path(source_folder).resolve()
        output_root = Path(output_folder).resolve()
        if not source_root.exists() or not source_root.is_dir():
            msg = f"source_folder must be an existing directory: {source_root}"
            raise ValueError(msg)
        source_root = self._resolve_source_root(source_root, output_root)
        snapshots = self._scan_sources(source_root, output_root)
        return tuple((snapshot.rel_path, snapshot.sha256) for snapshot in snapshots)

    def _resolve_source_root(self, source_root: Path, output_root: Path) -> Path:
        if source_root != output_root:
            return source_root
        raw_data_dir = output_root / self.config.raw_data_dir_name
        manifest_path = output_root / self.config.metadata_dir_name / "manifest.json"
        if raw_data_dir.exists() and raw_data_dir.is_dir() and manifest_path.exists():
            return raw_data_dir.resolve()
        return source_root

    def _is_generated_path(self, path: Path, source_root: Path, output_root: Path) -> bool:
        if self._is_output_tree_path(path, source_root, output_root):
            return True
        try:
            rel = path.relative_to(output_root)
        except ValueError:
            return False
        if not rel.parts:
            return False
        generated_names = {
            self.config.metadata_dir_name,
            self.config.raw_data_dir_name,
            "memory",
            "soul",
            "skill",
        }
        if rel.parts[0] == self.config.raw_data_dir_name:
            raw_data_dir = (output_root / self.config.raw_data_dir_name).resolve()
            try:
                source_root.relative_to(raw_data_dir)
            except ValueError:
                pass
            else:
                return False
        if rel.parts[0] in generated_names:
            return True
        return rel.as_posix() in {"memory.md", "soul.md", "skill.md"}

    def _effective_exclude_patterns(self, source_root: Path, output_root: Path) -> tuple[str, ...]:
        patterns: list[str] = list(self.config.exclude_patterns)
        patterns.extend(self._ignore_file_patterns(source_root / self.config.ignore_file_name))
        if output_root != source_root:
            patterns.extend(self._ignore_file_patterns(output_root / self.config.ignore_file_name))
        patterns.append(self.config.ignore_file_name)
        return tuple(_dedupe_ordered(patterns))

    def _ignore_file_patterns(self, path: Path) -> list[str]:
        if not path.is_file():
            return []
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except UnicodeDecodeError:
            return []
        patterns: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            patterns.append(stripped)
        return patterns

    def _is_excluded_source_path(
        self,
        path: Path,
        source_root: Path,
        exclude_patterns: Sequence[str],
    ) -> bool:
        try:
            rel_path = _to_posix(path.relative_to(source_root))
        except ValueError:
            return False
        return any(self._matches_exclude_pattern(rel_path, pattern) for pattern in exclude_patterns)

    def _matches_exclude_pattern(self, rel_path: str, pattern: str) -> bool:
        clean = pattern.replace("\\", "/").strip().lstrip("/")
        if not clean:
            return False
        if fnmatch.fnmatchcase(rel_path, clean):
            return True
        if "/" not in clean and fnmatch.fnmatchcase(Path(rel_path).name, clean):
            return True
        literal = clean.rstrip("/")
        if not any(char in literal for char in "*?[]"):
            return rel_path == literal or rel_path.startswith(f"{literal}/")
        return False

    def _is_output_tree_path(self, path: Path, source_root: Path, output_root: Path) -> bool:
        if source_root == output_root:
            return False
        try:
            output_root.relative_to(source_root)
        except ValueError:
            return False
        try:
            path.relative_to(output_root)
        except ValueError:
            return False
        return True

    def _sync_raw_file(self, snapshot: _SourceSnapshot, raw_data_dir: Path) -> None:
        self._copy_raw_path(snapshot.absolute_path, raw_data_dir / snapshot.rel_path)
        for sidecar_path, sidecar_rel_path in zip(snapshot.sidecar_paths, snapshot.sidecar_rel_paths, strict=True):
            self._copy_raw_path(sidecar_path, raw_data_dir / sidecar_rel_path)

    def _copy_raw_path(self, source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() == destination.resolve():
            return
        shutil.copy2(source, destination)

    def _expected_raw_rel_paths(self, snapshots: Sequence[_SourceSnapshot]) -> set[str]:
        expected: set[str] = set()
        for snapshot in snapshots:
            expected.add(snapshot.raw_rel_path)
            for sidecar_rel_path in snapshot.sidecar_rel_paths:
                expected.add(f"{self.config.raw_data_dir_name}/{sidecar_rel_path}")
        return expected

    def _expected_evidence_rel_paths(self, snapshots: Sequence[_SourceSnapshot]) -> set[str]:
        return {snapshot.evidence_rel_path for snapshot in snapshots}

    def _source_entries_from_manifest(self, source: Any) -> list[MarkdownMemoryEntry]:
        if not isinstance(source, Mapping):
            return []
        entries: list[MarkdownMemoryEntry] = []
        for entry_data in source.get("entries", []):
            if isinstance(entry_data, Mapping):
                entries.append(MarkdownMemoryEntry.from_manifest(entry_data))
        return entries

    def _entry_manifests_from_source(self, source: Mapping[str, Any]) -> list[dict[str, Any]]:
        return [entry.to_manifest() for entry in self._source_entries_from_manifest(source)]

    def _evolve_removed_source(self, rel_path: str, previous: Mapping[str, Any]) -> EvolutionReviewBundle:
        previous_entries = self._source_entries_from_manifest(previous)
        evidence_path = str(previous.get("evidence", ""))
        raw_path = str(previous.get("raw_path", f"{self.config.raw_data_dir_name}/{rel_path}"))
        return self.self_evolve.build_for_removed_source(
            source=raw_path,
            evidence_path=evidence_path,
            previous_entries=[entry.to_manifest() for entry in previous_entries],
        )

    def _expected_raw_rel_paths_from_sources(self, sources: Mapping[str, Any]) -> set[str]:
        expected: set[str] = set()
        for source in sources.values():
            if not isinstance(source, Mapping):
                continue
            raw_path = source.get("raw_path")
            if isinstance(raw_path, str) and raw_path:
                expected.add(raw_path)
            for sidecar in source.get("sidecars", []):
                sidecar_path = str(sidecar)
                if not sidecar_path:
                    continue
                if sidecar_path.startswith(f"{self.config.raw_data_dir_name}/"):
                    expected.add(sidecar_path)
                else:
                    expected.add(f"{self.config.raw_data_dir_name}/{sidecar_path}")
        return expected

    def _expected_evidence_rel_paths_from_sources(self, sources: Mapping[str, Any]) -> set[str]:
        expected: set[str] = set()
        for source in sources.values():
            if not isinstance(source, Mapping):
                continue
            evidence_path = source.get("evidence")
            if isinstance(evidence_path, str) and evidence_path:
                expected.add(evidence_path)
        return expected

    def _remove_stale_raw_files(self, raw_data_dir: Path, expected_raw_rel_paths: set[str]) -> None:
        expected = {rel.removeprefix(f"{self.config.raw_data_dir_name}/") for rel in expected_raw_rel_paths}
        for path in sorted(raw_data_dir.rglob("*"), reverse=True):
            if path.is_file() and _to_posix(path.relative_to(raw_data_dir)) not in expected:
                path.unlink()
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()

    def _remove_stale_evidence_files(self, derived_dir: Path, expected_evidence_rel_paths: set[str]) -> None:
        expected = {
            rel.removeprefix(f"{self.config.metadata_dir_name}/{self.config.derived_dir_name}/")
            for rel in expected_evidence_rel_paths
        }
        if not derived_dir.exists():
            return
        for path in sorted(derived_dir.rglob("*"), reverse=True):
            if path.is_file() and path.name.endswith(".evidence.md"):
                if _to_posix(path.relative_to(derived_dir)) not in expected:
                    path.unlink()
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()

    async def _extract_entries(
        self,
        snapshot: _SourceSnapshot,
        output_root: Path,
        *,
        previous: Any,
        user: Mapping[str, Any] | None,
    ) -> _SourceExtraction:
        evidence_text = self._build_evidence(snapshot)
        service_extraction = await self._extract_with_memory_service(snapshot, user=user)
        if service_extraction is not None:
            evidence_text = evidence_text.rstrip() + "\n\n" + service_extraction.evidence_text.strip() + "\n"

        evidence_path = output_root / snapshot.evidence_rel_path
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(evidence_text, encoding="utf-8")

        if service_extraction is not None and service_extraction.entries:
            candidate_entries = service_extraction.entries
        else:
            candidate_entries = self._extract_with_local_heuristics(snapshot, evidence_text)

        if not self.config.self_evolve_enabled:
            return _SourceExtraction(entries=candidate_entries, instructions=[], proposals=[], reviews=[])

        previous_entries = self._source_entries_from_manifest(previous)
        bundle = self.self_evolve.build_for_source(
            source=snapshot.raw_rel_path,
            evidence_path=snapshot.evidence_rel_path,
            evidence_text=evidence_text,
            candidates=[entry.to_manifest() for entry in candidate_entries],
            previous_entries=[entry.to_manifest() for entry in previous_entries],
        )
        approved_entries = [
            MarkdownMemoryEntry.from_manifest(entry)
            for entry in apply_reviewed_proposals(
                [entry.to_manifest() for entry in previous_entries],
                bundle.proposals,
                bundle.reviews,
            )
        ]
        return _SourceExtraction(
            entries=approved_entries,
            instructions=bundle.instructions,
            proposals=bundle.proposals,
            reviews=bundle.reviews,
        )

    async def _extract_with_memory_service(
        self,
        snapshot: _SourceSnapshot,
        *,
        user: Mapping[str, Any] | None,
    ) -> _ServiceExtraction | None:
        if not self.memory_service or not self.config.use_memory_service:
            return None
        service_modality = self._service_modality(snapshot)
        if service_modality is None:
            return None
        try:
            result = await self.memory_service.memorize(
                resource_url=str(snapshot.absolute_path),
                modality=service_modality,
                user=dict(user or {}),
            )
        except Exception as exc:
            evidence_text = (
                "## MemoryService Extraction\n\n"
                f"MemoryService extraction was attempted for `{snapshot.raw_rel_path}` "
                f"with modality `{service_modality}` but failed: {type(exc).__name__}: {exc}\n"
            )
            return _ServiceExtraction(entries=[], evidence_text=evidence_text)

        entries: list[MarkdownMemoryEntry] = []
        for idx, item in enumerate(result.get("items", []), start=1):
            if not isinstance(item, Mapping):
                continue
            summary = str(item.get("summary", "")).strip()
            if not summary:
                continue
            memory_type = str(item.get("memory_type", "knowledge"))
            bucket = self._bucket_from_memory_type(memory_type, summary)
            entries.append(
                MarkdownMemoryEntry(
                    id=self._entry_id(bucket, snapshot.rel_path, idx),
                    bucket=bucket,
                    title=self._title_for(snapshot.rel_path, summary),
                    body=summary,
                    source=snapshot.raw_rel_path,
                    evidence=snapshot.evidence_rel_path,
                    modality=snapshot.modality,
                    confidence="high",
                    tags=[memory_type, "llm-extracted"],
                )
            )
        return _ServiceExtraction(entries=entries, evidence_text=self._build_service_evidence(snapshot, result))

    def _build_service_evidence(self, snapshot: _SourceSnapshot, result: Mapping[str, Any]) -> str:
        lines = [
            "## MemoryService Extraction",
            "",
            f"- source: {snapshot.raw_rel_path}",
            f"- modality: {snapshot.modality}",
            "",
        ]

        resources = self._as_list(result.get("resources"))
        resource = result.get("resource")
        if isinstance(resource, Mapping):
            resources.insert(0, resource)
        resource_lines = self._format_service_records("Resource", resources, keys=("url", "caption", "modality"))
        if resource_lines:
            lines.extend(["### Resources", "", *resource_lines, ""])

        item_lines = self._format_service_records(
            "Item",
            self._as_list(result.get("items")),
            keys=("memory_type", "summary"),
        )
        if item_lines:
            lines.extend(["### Items", "", *item_lines, ""])

        category_lines = self._format_service_records(
            "Category",
            self._as_list(result.get("categories")),
            keys=("name", "description", "summary"),
        )
        if category_lines:
            lines.extend(["### Categories", "", *category_lines, ""])

        if len(lines) == 5:
            lines.append("MemoryService returned no structured resources, items, or categories.")
        return "\n".join(lines).rstrip() + "\n"

    def _format_service_records(
        self,
        label: str,
        records: Sequence[Any],
        *,
        keys: Sequence[str],
    ) -> list[str]:
        lines: list[str] = []
        for idx, record in enumerate(records, start=1):
            if not isinstance(record, Mapping):
                continue
            lines.append(f"{idx}. {label}")
            for key in keys:
                value = record.get(key)
                if value is None or value == "":
                    continue
                lines.append(f"   - {key}: {self._single_line(str(value))}")
        return lines

    def _as_list(self, value: Any) -> list[Any]:
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        return []

    def _single_line(self, value: str) -> str:
        compact = " ".join(value.split())
        if len(compact) > 500:
            return compact[:497].rstrip() + "..."
        return compact

    def _extract_with_local_heuristics(
        self,
        snapshot: _SourceSnapshot,
        evidence_text: str,
    ) -> list[MarkdownMemoryEntry]:
        buckets: list[MemoryBucket] = ["memory"]
        searchable = evidence_text.lower()
        if self._contains_any(searchable, _SOUL_KEYWORDS):
            buckets.append("soul")
        if self._contains_any(searchable, _SKILL_KEYWORDS):
            buckets.append("skill")

        entries: list[MarkdownMemoryEntry] = []
        for idx, bucket in enumerate(buckets, start=1):
            body = self._fallback_body(bucket, snapshot, evidence_text)
            entries.append(
                MarkdownMemoryEntry(
                    id=self._entry_id(bucket, snapshot.rel_path, idx),
                    bucket=bucket,
                    title=self._fallback_title(bucket, snapshot.rel_path),
                    body=body,
                    source=snapshot.raw_rel_path,
                    evidence=snapshot.evidence_rel_path,
                    modality=snapshot.modality,
                    confidence="low"
                    if snapshot.modality in {"image", "audio", "video", "document", "binary"}
                    else "medium",
                    tags=[snapshot.modality, "local-extraction"],
                )
            )
        return entries

    def _build_evidence(self, snapshot: _SourceSnapshot) -> str:
        header = (
            f"# Evidence: {snapshot.rel_path}\n\n"
            f"- source: {snapshot.raw_rel_path}\n"
            f"- modality: {snapshot.modality}\n"
            f"- sha256: {snapshot.sha256}\n"
            f"- size_bytes: {snapshot.size}\n"
            f"- extracted_at: {_utc_now()}\n\n"
        )
        text = self._read_text_evidence(snapshot.absolute_path)
        if text is None:
            sidecar_evidence = self._build_sidecar_evidence(snapshot.sidecar_paths)
            return (
                header
                + "## Multimodal Evidence\n\n"
                + "This source is preserved as raw multimodal data. "
                + "Use a MemoryService with multimodal or document-capable LLM profiles "
                + "to derive captions, transcripts, frame descriptions, or document summaries.\n"
                + sidecar_evidence
            )
        return header + "## Text Evidence\n\n" + text.strip() + "\n"

    def _build_sidecar_evidence(self, sidecars: Sequence[Path]) -> str:
        if not sidecars:
            return ""

        lines = ["\n## Sidecar Evidence", ""]
        for sidecar in sidecars:
            text = self._read_sidecar_text(sidecar)
            if text is None:
                continue
            lines.extend(
                [
                    f"### {sidecar.name}",
                    "",
                    text.strip(),
                    "",
                ]
            )
        if len(lines) == 2:
            return ""
        return "\n".join(lines).rstrip() + "\n"

    def _find_sidecar_files(
        self,
        path: Path,
        source_root: Path,
        exclude_patterns: Sequence[str],
    ) -> list[Path]:
        candidates: list[Path] = []
        for label in _SIDECAR_LABELS:
            for extension in _SIDECAR_TEXT_EXTENSIONS:
                candidates.append(path.with_name(f"{path.name}.{label}{extension}"))
                candidates.append(path.with_name(f"{path.stem}.{label}{extension}"))
        seen: set[Path] = set()
        sidecars: list[Path] = []
        for candidate in candidates:
            if candidate in seen or candidate == path:
                continue
            seen.add(candidate)
            if self._is_excluded_source_path(candidate, source_root, exclude_patterns):
                continue
            if candidate.exists() and candidate.is_file():
                sidecars.append(candidate)
        return sidecars

    def _is_paired_sidecar(self, path: Path, source_files: set[Path]) -> bool:
        return self._paired_sidecar_source(path, source_files) is not None

    def _paired_sidecar_source(self, path: Path, source_files: set[Path]) -> Path | None:
        if path.suffix.lower() not in _SIDECAR_TEXT_EXTENSIONS:
            return None
        name_without_extension = path.name[: -len(path.suffix)]
        for label in _SIDECAR_LABELS:
            suffix = f".{label}"
            if not name_without_extension.endswith(suffix):
                continue
            base_name = name_without_extension[: -len(suffix)]
            exact_source = path.with_name(base_name)
            if exact_source in source_files and self._supports_sidecars(self._detect_modality(exact_source)):
                return exact_source
            for candidate in source_files:
                if candidate.parent == path.parent and candidate.stem == base_name:
                    if self._supports_sidecars(self._detect_modality(candidate)):
                        return candidate
        return None

    def _supports_sidecars(self, modality: str) -> bool:
        return modality in _SIDECAR_SOURCE_MODALITIES

    def _read_sidecar_text(self, path: Path) -> str | None:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            return None
        if path.suffix.lower() == ".json":
            text = self._format_json_sidecar(text)
        elif path.suffix.lower() == ".jsonl":
            text = self._format_jsonl_sidecar(text)
        if len(text) > self.config.max_text_chars:
            return text[: self.config.max_text_chars] + "\n\n[Truncated by FolderMemoryCompiler]\n"
        return text

    def _format_json_sidecar(self, text: str) -> str:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return text
        formatted = json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=True)
        return "Structured JSON sidecar:\n\n```json\n" + formatted + "\n```\n"

    def _format_jsonl_sidecar(self, text: str) -> str:
        formatted_lines: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return text
            formatted_lines.append(json.dumps(parsed, ensure_ascii=False, sort_keys=True))
        if not formatted_lines:
            return text
        return "Structured JSONL sidecar:\n\n```jsonl\n" + "\n".join(formatted_lines) + "\n```\n"

    def _read_text_evidence(self, path: Path) -> str | None:
        if self._detect_modality(path) in {"image", "audio", "video", "document", "binary"}:
            return None
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            return None
        if len(text) > self.config.max_text_chars:
            return text[: self.config.max_text_chars] + "\n\n[Truncated by FolderMemoryCompiler]\n"
        return text

    def _service_modality(self, snapshot: _SourceSnapshot) -> str | None:
        if snapshot.modality in {"image", "audio", "video", "conversation"}:
            return snapshot.modality
        if snapshot.modality in {"text", "document", "code"}:
            return "document"
        return None

    def _detect_modality(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in _IMAGE_EXTENSIONS:
            return "image"
        if suffix in _AUDIO_EXTENSIONS:
            return "audio"
        if suffix in _VIDEO_EXTENSIONS:
            return "video"
        if suffix in _CONVERSATION_EXTENSIONS or self._looks_like_conversation_path(path):
            return "conversation"
        if suffix in _CODE_EXTENSIONS:
            return "code"
        if suffix in _TEXT_EXTENSIONS:
            return "text"
        if suffix in _DOCUMENT_EXTENSIONS:
            return "document"
        return "binary"

    def _looks_like_conversation_path(self, path: Path) -> bool:
        lowered = path.as_posix().lower()
        return any(part in lowered for part in ("chat", "conversation", "dialog", "message"))

    def _bucket_from_memory_type(self, memory_type: str, summary: str) -> MemoryBucket:
        lowered = f"{memory_type} {summary}".lower()
        if memory_type in {"skill", "tool"} or self._contains_any(lowered, _SKILL_KEYWORDS):
            return "skill"
        if self._contains_any(lowered, _SOUL_KEYWORDS):
            return "soul"
        return "memory"

    def _fallback_title(self, bucket: MemoryBucket, rel_path: str) -> str:
        source_name = Path(rel_path).stem.replace("_", " ").replace("-", " ").strip() or rel_path
        if bucket == "soul":
            return f"Persona and style signals from {source_name}"
        if bucket == "skill":
            return f"Skill signals from {source_name}"
        return f"Memory extracted from {source_name}"

    def _fallback_body(self, bucket: MemoryBucket, snapshot: _SourceSnapshot, evidence_text: str) -> str:
        if snapshot.modality in {"image", "audio", "video", "document", "binary"}:
            if "## Sidecar Evidence" in evidence_text:
                excerpt = self._compact_excerpt(evidence_text)
                if bucket == "soul":
                    prefix = "This multimodal source includes sidecar persona, tone, or style evidence."
                elif bucket == "skill":
                    prefix = "This multimodal source includes sidecar skill, workflow, or tool-use evidence."
                else:
                    prefix = "This multimodal source includes sidecar memory evidence."
                return f"{prefix}\n\nEvidence excerpt:\n\n> {excerpt}"
            return (
                f"`{snapshot.raw_rel_path}` is preserved as {snapshot.modality} raw data. "
                "The compiler created traceable evidence metadata; richer semantic extraction can be produced "
                "with a multimodal MemoryService."
            )
        if bucket == "skill" and "# Skill Evolution Trace" in evidence_text:
            return self._skill_trace_body(evidence_text)

        excerpt = self._compact_excerpt(evidence_text)
        if bucket == "soul":
            prefix = "This source contains persona, tone, language-style, or interaction-style signals."
        elif bucket == "skill":
            prefix = "This source contains skill, workflow, tool-use, or capability signals."
        else:
            prefix = "This source contributes durable memory evidence."
        return f"{prefix}\n\nEvidence excerpt:\n\n> {excerpt}"

    def _skill_trace_body(self, evidence_text: str) -> str:
        sections = {
            "summary": self._markdown_section(evidence_text, "Summary"),
            "actions": self._markdown_section(evidence_text, "Actions"),
            "tools": self._markdown_section(evidence_text, "Tool Calls"),
            "lessons": self._markdown_section(evidence_text, "Lessons For Skill Evolution"),
            "hints": self._markdown_section(evidence_text, "Retrieval Hints"),
        }
        lines = [
            "This source is a skill evolution trace. It records an agent/tool execution and the reusable lessons "
            "that should improve future behavior.",
            "",
        ]
        for label, content in (
            ("Summary", sections["summary"]),
            ("Actions", sections["actions"]),
            ("Tool Calls", sections["tools"]),
            ("Lessons", sections["lessons"]),
            ("Retrieval Hints", sections["hints"]),
        ):
            if content:
                lines.extend([f"**{label}**", "", content, ""])
        return "\n".join(lines).strip()

    def _markdown_section(self, text: str, heading: str) -> str:
        marker = f"## {heading}"
        start = text.find(marker)
        if start == -1:
            return ""
        start += len(marker)
        end = text.find("\n## ", start)
        section = text[start:] if end == -1 else text[start:end]
        return section.strip()

    def _compact_excerpt(self, text: str) -> str:
        content = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        if len(content) > 700:
            content = content[:700].rstrip() + "..."
        return content.replace("\n", "\n> ")

    def _title_for(self, rel_path: str, summary: str) -> str:
        first_line = summary.splitlines()[0].strip()
        if len(first_line) > 80:
            return first_line[:77].rstrip() + "..."
        return first_line or self._fallback_title("memory", rel_path)

    def _entry_id(self, bucket: MemoryBucket, rel_path: str, idx: int) -> str:
        digest = hashlib.sha256(f"{bucket}:{rel_path}:{idx}".encode("utf-8")).hexdigest()[:12]
        prefix = {"memory": "mem", "soul": "soul", "skill": "skill"}[bucket]
        return f"{prefix}_{digest}"

    def _hash_source(self, path: Path, sidecars: Sequence[Path]) -> str:
        digest = hashlib.sha256()
        digest.update(b"source\0")
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        self._update_digest_from_file(digest, path)
        for sidecar in sidecars:
            digest.update(b"\0sidecar\0")
            digest.update(sidecar.name.encode("utf-8"))
            digest.update(b"\0")
            self._update_digest_from_file(digest, sidecar)
        return digest.hexdigest()

    def _hash_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        self._update_digest_from_file(digest, path)
        return digest.hexdigest()

    def _update_digest_from_file(self, digest: Any, path: Path) -> None:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)

    def _load_manifest(self, manifest_path: Path) -> dict[str, Any]:
        if not manifest_path.exists():
            return {"version": 1, "sources": {}}
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"version": 1, "sources": {}}
        return loaded if isinstance(loaded, dict) else {"version": 1, "sources": {}}

    def _write_manifest(self, manifest_path: Path, manifest: Mapping[str, Any]) -> None:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    def _entries_from_manifest(self, manifest: Mapping[str, Any]) -> list[MarkdownMemoryEntry]:
        entries: list[MarkdownMemoryEntry] = []
        sources = manifest.get("sources", {})
        if not isinstance(sources, Mapping):
            return entries
        for source in sources.values():
            if not isinstance(source, Mapping):
                continue
            for entry_data in source.get("entries", []):
                if isinstance(entry_data, Mapping):
                    entries.append(MarkdownMemoryEntry.from_manifest(entry_data))
        return entries

    def _write_markdown_repository(self, output_root: Path, entries: Sequence[MarkdownMemoryEntry]) -> None:
        for bucket in ("memory", "soul", "skill"):
            bucket_entries = [entry for entry in entries if entry.bucket == bucket]
            self._write_top_level_file(output_root, cast(MemoryBucket, bucket), bucket_entries)
            self._write_detail_files(output_root, cast(MemoryBucket, bucket), bucket_entries)

    def _write_top_level_file(
        self,
        output_root: Path,
        bucket: MemoryBucket,
        entries: Sequence[MarkdownMemoryEntry],
    ) -> None:
        target = output_root / f"{bucket}.md"
        title = {"memory": "Memory", "soul": "Soul", "skill": "Skill"}[bucket]
        generated = self._render_entries(title, entries)
        self._write_generated_block(target, title, generated)

    def _write_detail_files(
        self,
        output_root: Path,
        bucket: MemoryBucket,
        entries: Sequence[MarkdownMemoryEntry],
    ) -> None:
        bucket_dir = output_root / bucket
        expected_files: set[Path] = set()
        by_source: dict[str, list[MarkdownMemoryEntry]] = {}
        for entry in entries:
            by_source.setdefault(entry.source, []).append(entry)
        for source, source_entries in by_source.items():
            detail_file = bucket_dir / f"{_safe_markdown_name(source)}.md"
            expected_files.add(detail_file)
            generated = self._render_entries(f"{bucket.title()} From {source}", source_entries)
            self._write_generated_block(detail_file, f"{bucket.title()} From {source}", generated)

        for path in bucket_dir.glob("*.md"):
            if path not in expected_files:
                self._remove_stale_detail_file(path, bucket)

    def _remove_stale_detail_file(self, path: Path, bucket: MemoryBucket) -> None:
        try:
            current = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            return
        if GENERATED_START not in current or GENERATED_END not in current:
            return
        if self._manual_detail_content(current, bucket):
            title = self._detail_title_from_content(current) or f"{bucket.title()} Notes"
            self._write_generated_block(path, title, "No generated entries yet.\n")
            return
        path.unlink()

    def _manual_detail_content(self, current: str, bucket: MemoryBucket) -> str:
        without_block = self._remove_generated_block_text(current).strip()
        if not without_block:
            return ""
        lines = without_block.splitlines()
        first = lines[0].strip()
        rest = "\n".join(lines[1:]).strip()
        bucket_title = bucket.title()
        if first == f"# {bucket_title}" or first.startswith(f"# {bucket_title} From "):
            return rest
        return without_block

    def _remove_generated_block_text(self, current: str) -> str:
        start_idx = current.find(GENERATED_START)
        end_idx = current.find(GENERATED_END)
        if start_idx == -1 or end_idx == -1 or end_idx < start_idx:
            return current
        end_idx += len(GENERATED_END)
        return current[:start_idx] + current[end_idx:]

    def _detail_title_from_content(self, current: str) -> str | None:
        for line in current.splitlines():
            if line.startswith("# "):
                return line[2:].strip() or None
        return None

    def _render_entries(self, title: str, entries: Sequence[MarkdownMemoryEntry]) -> str:
        if not entries:
            return "No generated entries yet.\n"
        rendered = [entry.to_markdown() for entry in entries]
        return "\n".join(rendered).strip() + "\n"

    def _write_generated_block(self, target: Path, title: str, generated: str) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        block = f"{GENERATED_START}\n{generated.strip()}\n{GENERATED_END}\n"
        if not target.exists():
            content = f"# {title}\n\n{block}\n"
        else:
            current = target.read_text(encoding="utf-8-sig")
            content = self._replace_generated_block(current, block)
        target.write_text(content, encoding="utf-8")

    def _replace_generated_block(self, current: str, block: str) -> str:
        start_idx = current.find(GENERATED_START)
        end_idx = current.find(GENERATED_END)
        if start_idx == -1 or end_idx == -1 or end_idx < start_idx:
            return current.rstrip() + "\n\n" + block
        end_idx += len(GENERATED_END)
        return current[:start_idx] + block.rstrip() + current[end_idx:]

    def _contains_any(self, value: str, needles: Sequence[str]) -> bool:
        return any(needle in value for needle in needles)


async def compile_folder_to_markdown(
    source_folder: str | Path,
    output_folder: str | Path,
    *,
    memory_service: MemoryService | None = None,
    user: Mapping[str, Any] | None = None,
    config: FolderMemoryCompilerConfig | None = None,
) -> FolderCompileResult:
    compiler = FolderMemoryCompiler(memory_service=memory_service, config=config)
    return await compiler.compile(source_folder, output_folder, user=user)


def compile_folder_to_markdown_sync(
    source_folder: str | Path,
    output_folder: str | Path,
    *,
    memory_service: MemoryService | None = None,
    user: Mapping[str, Any] | None = None,
    config: FolderMemoryCompilerConfig | None = None,
) -> FolderCompileResult:
    return asyncio.run(
        compile_folder_to_markdown(
            source_folder,
            output_folder,
            memory_service=memory_service,
            user=user,
            config=config,
        )
    )


def scaffold_folder_memory_repository(
    output_folder: str | Path,
    *,
    source_folder: str | Path | None = None,
    config: FolderMemoryCompilerConfig | None = None,
) -> FolderScaffoldResult:
    compiler = FolderMemoryCompiler(config=config)
    return compiler.scaffold(output_folder, source_folder=source_folder)


def inspect_folder_memory_status(
    source_folder: str | Path,
    output_folder: str | Path,
    *,
    config: FolderMemoryCompilerConfig | None = None,
) -> FolderStatusResult:
    compiler = FolderMemoryCompiler(config=config)
    return compiler.status(source_folder, output_folder)


def inspect_folder_memory_health(
    output_folder: str | Path,
    *,
    config: FolderMemoryCompilerConfig | None = None,
) -> FolderHealthResult:
    compiler = FolderMemoryCompiler(config=config)
    return compiler.health(output_folder)


def review_folder_evolution(
    output_folder: str | Path,
    *,
    proposal_ids: Sequence[str] | None = None,
    reviewer: str = "creator",
    decision: ReviewStatus = "approved",
    reason: str = "",
    config: FolderMemoryCompilerConfig | None = None,
) -> EvolutionReviewApplyResult:
    compiler = FolderMemoryCompiler(config=config)
    return compiler.review_evolution(
        output_folder,
        proposal_ids=proposal_ids,
        reviewer=reviewer,
        decision=decision,
        reason=reason,
    )


async def watch_folder_to_markdown(
    source_folder: str | Path,
    output_folder: str | Path,
    *,
    memory_service: MemoryService | None = None,
    user: Mapping[str, Any] | None = None,
    config: FolderMemoryCompilerConfig | None = None,
    poll_interval: float = 2.0,
    max_runs: int | None = None,
    on_event: Callable[[FolderWatchEvent], Any | Awaitable[Any]] | None = None,
) -> list[FolderWatchEvent]:
    if poll_interval <= 0:
        msg = "poll_interval must be greater than 0"
        raise ValueError(msg)
    if max_runs is not None and max_runs <= 0:
        msg = "max_runs must be greater than 0 when provided"
        raise ValueError(msg)

    compiler = FolderMemoryCompiler(memory_service=memory_service, config=config)
    source_root = Path(source_folder).resolve()
    output_root = Path(output_folder).resolve()
    last_fingerprint: tuple[tuple[str, str], ...] | None = None
    events: list[FolderWatchEvent] = []
    iteration = 0

    while max_runs is None or len(events) < max_runs:
        fingerprint = compiler.source_fingerprint(source_root, output_root)
        if last_fingerprint is None or fingerprint != last_fingerprint:
            reason: FolderWatchReason = "initial" if last_fingerprint is None else "changed"
            status = compiler.status(source_root, output_root)
            result = await compiler.compile(source_root, output_root, user=user)
            last_fingerprint = compiler.source_fingerprint(source_root, output_root)
            iteration += 1
            event = FolderWatchEvent(iteration=iteration, reason=reason, result=result, status=status)
            events.append(event)
            if on_event is not None:
                callback_result = on_event(event)
                if inspect.isawaitable(callback_result):
                    await callback_result
            if max_runs is not None and len(events) >= max_runs:
                break
        await asyncio.sleep(poll_interval)

    return events


def watch_folder_to_markdown_sync(
    source_folder: str | Path,
    output_folder: str | Path,
    *,
    memory_service: MemoryService | None = None,
    user: Mapping[str, Any] | None = None,
    config: FolderMemoryCompilerConfig | None = None,
    poll_interval: float = 2.0,
    max_runs: int | None = None,
    on_event: Callable[[FolderWatchEvent], Any | Awaitable[Any]] | None = None,
) -> list[FolderWatchEvent]:
    return asyncio.run(
        watch_folder_to_markdown(
            source_folder,
            output_folder,
            memory_service=memory_service,
            user=user,
            config=config,
            poll_interval=poll_interval,
            max_runs=max_runs,
            on_event=on_event,
        )
    )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _to_posix(path: Path) -> str:
    return path.as_posix()


def _dedupe_ordered(values: Sequence[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = value.strip()
        if clean and clean not in seen:
            deduped.append(clean)
            seen.add(clean)
    return deduped


def _relative_to(path: Path, root: Path) -> str:
    try:
        rel_path = path.relative_to(root)
    except ValueError:
        return str(path)
    if not rel_path.parts:
        return "."
    return rel_path.as_posix()


def _safe_markdown_name(source: str) -> str:
    clean = source.removeprefix("raw_data/")
    clean = clean.replace("\\", "/").replace("/", "__")
    clean = clean.replace(":", "_")
    return clean or "source"


_TEXT_EXTENSIONS = {
    ".csv",
    ".htm",
    ".html",
    ".json",
    ".jsonl",
    ".log",
    ".md",
    ".rst",
    ".text",
    ".toml",
    ".tsv",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}

_CONVERSATION_EXTENSIONS = {".chat"}

_DOCUMENT_EXTENSIONS = {".doc", ".docx", ".pdf", ".ppt", ".pptx", ".xls", ".xlsx"}

_CODE_EXTENSIONS = {
    ".c",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".lua",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".sql",
    ".swift",
    ".ts",
    ".tsx",
}

_IMAGE_EXTENSIONS = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".tif", ".tiff", ".webp"}

_AUDIO_EXTENSIONS = {".aac", ".flac", ".m4a", ".mp3", ".mpga", ".ogg", ".opus", ".wav", ".webm"}

_VIDEO_EXTENSIONS = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg", ".webm"}

_SIDECAR_LABELS = (
    "alt",
    "caption",
    "description",
    "frames",
    "meta",
    "metadata",
    "notes",
    "ocr",
    "summary",
    "transcript",
)

_SIDECAR_TEXT_EXTENSIONS = (
    ".json",
    ".jsonl",
    ".md",
    ".txt",
)

_SIDECAR_SOURCE_MODALITIES = {"audio", "binary", "document", "image", "video"}

_SOUL_KEYWORDS = (
    "persona",
    "personality",
    "soul",
    "tone",
    "voice",
    "writing style",
    "language style",
    "interaction style",
    "\u4eba\u8bbe",
    "\u4eba\u683c",
    "\u8bed\u6c14",
    "\u8bed\u8c03",
    "\u8bed\u8a00\u98ce\u683c",
    "\u8868\u8fbe\u98ce\u683c",
)

_SKILL_KEYWORDS = (
    "ability",
    "capability",
    "skill",
    "tool",
    "workflow",
    "procedure",
    "playbook",
    "how to",
    "lesson learned",
    "\u6280\u80fd",
    "\u80fd\u529b",
    "\u5de5\u5177",
    "\u5de5\u4f5c\u6d41",
    "\u6d41\u7a0b",
    "\u65b9\u6cd5",
    "\u7ecf\u9a8c",
)


__all__ = [
    "EvolutionReviewApplyResult",
    "FolderCompileResult",
    "FolderHealthIssue",
    "FolderHealthResult",
    "FolderHealthSeverity",
    "FolderMemoryCompiler",
    "FolderMemoryCompilerConfig",
    "FolderScaffoldResult",
    "FolderSourceState",
    "FolderSourceStatus",
    "FolderStatusResult",
    "FolderWatchEvent",
    "MarkdownMemoryEntry",
    "compile_folder_to_markdown",
    "compile_folder_to_markdown_sync",
    "inspect_folder_memory_health",
    "inspect_folder_memory_status",
    "review_folder_evolution",
    "scaffold_folder_memory_repository",
    "watch_folder_to_markdown",
    "watch_folder_to_markdown_sync",
]
