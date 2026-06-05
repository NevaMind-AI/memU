from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast


EvolutionTarget = Literal["memory", "soul", "skill"]
EvolutionOperation = Literal["add", "update", "delete"]
EvolutionPriority = Literal["low", "medium", "high"]
EvolutionSourceKind = Literal["agent_log", "creator_feedback", "user_upload", "observation", "unknown"]
ReviewStatus = Literal["approved", "needs_review", "rejected"]


@dataclass(frozen=True)
class EvolutionReviewConfig:
    """Policy used by the review gate before patches update long-term context."""

    auto_approve: bool = True
    min_confidence: float = 0.0
    require_traceable_evidence: bool = True
    require_conflict_review: bool = True


@dataclass(frozen=True)
class EvidenceRecord:
    """Traceable evidence summary used by an evolution instruction."""

    source: str
    evidence_path: str
    source_kind: EvolutionSourceKind
    attribution: str
    summary: str
    conflicts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "evidence_path": self.evidence_path,
            "source_kind": self.source_kind,
            "attribution": self.attribution,
            "summary": self.summary,
            "conflicts": list(self.conflicts),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EvidenceRecord:
        return cls(
            source=str(data.get("source", "")),
            evidence_path=str(data.get("evidence_path", "")),
            source_kind=cast(EvolutionSourceKind, data.get("source_kind", "unknown")),
            attribution=str(data.get("attribution", "")),
            summary=str(data.get("summary", "")),
            conflicts=[str(item) for item in data.get("conflicts", [])],
        )


@dataclass(frozen=True)
class EvolutionInstruction:
    """Structured instruction distilled from raw evidence before any patch is proposed."""

    id: str
    target: EvolutionTarget
    operation: EvolutionOperation
    reason: str
    evidence: EvidenceRecord
    priority: EvolutionPriority
    confidence: float
    content: dict[str, Any]
    created_at: str = field(default_factory=lambda: _utc_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "target": self.target,
            "operation": self.operation,
            "reason": self.reason,
            "evidence": self.evidence.to_dict(),
            "priority": self.priority,
            "confidence": self.confidence,
            "content": dict(self.content),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EvolutionInstruction:
        evidence = data.get("evidence", {})
        return cls(
            id=str(data.get("id", "")),
            target=cast(EvolutionTarget, data.get("target", "memory")),
            operation=cast(EvolutionOperation, data.get("operation", "add")),
            reason=str(data.get("reason", "")),
            evidence=EvidenceRecord.from_dict(evidence if isinstance(evidence, Mapping) else {}),
            priority=cast(EvolutionPriority, data.get("priority", "medium")),
            confidence=float(data.get("confidence", 0.0)),
            content=dict(data.get("content", {})) if isinstance(data.get("content", {}), Mapping) else {},
            created_at=str(data.get("created_at") or _utc_now()),
        )


@dataclass(frozen=True)
class PatchProposal:
    """A proposed change to memory.md, soul.md, or skill.md derived from an instruction."""

    id: str
    instruction_id: str
    target: EvolutionTarget
    operation: EvolutionOperation
    target_path: str
    summary: str
    patch: dict[str, Any]
    reason: str
    evidence: EvidenceRecord
    priority: EvolutionPriority
    confidence: float
    created_at: str = field(default_factory=lambda: _utc_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "instruction_id": self.instruction_id,
            "target": self.target,
            "operation": self.operation,
            "target_path": self.target_path,
            "summary": self.summary,
            "patch": dict(self.patch),
            "reason": self.reason,
            "evidence": self.evidence.to_dict(),
            "priority": self.priority,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PatchProposal:
        evidence = data.get("evidence", {})
        return cls(
            id=str(data.get("id", "")),
            instruction_id=str(data.get("instruction_id", "")),
            target=cast(EvolutionTarget, data.get("target", "memory")),
            operation=cast(EvolutionOperation, data.get("operation", "add")),
            target_path=str(data.get("target_path", "memory.md")),
            summary=str(data.get("summary", "")),
            patch=dict(data.get("patch", {})) if isinstance(data.get("patch", {}), Mapping) else {},
            reason=str(data.get("reason", "")),
            evidence=EvidenceRecord.from_dict(evidence if isinstance(evidence, Mapping) else {}),
            priority=cast(EvolutionPriority, data.get("priority", "medium")),
            confidence=float(data.get("confidence", 0.0)),
            created_at=str(data.get("created_at") or _utc_now()),
        )


@dataclass(frozen=True)
class ReviewDecision:
    """Review-gate decision for a patch proposal."""

    proposal_id: str
    status: ReviewStatus
    reviewer: str
    reason: str
    confidence: float
    safety_flags: list[str] = field(default_factory=list)
    reviewed_at: str = field(default_factory=lambda: _utc_now())

    @property
    def approved(self) -> bool:
        return self.status == "approved"

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "status": self.status,
            "reviewer": self.reviewer,
            "reason": self.reason,
            "confidence": self.confidence,
            "safety_flags": list(self.safety_flags),
            "reviewed_at": self.reviewed_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ReviewDecision:
        return cls(
            proposal_id=str(data.get("proposal_id", "")),
            status=cast(ReviewStatus, data.get("status", "needs_review")),
            reviewer=str(data.get("reviewer", "")),
            reason=str(data.get("reason", "")),
            confidence=float(data.get("confidence", 0.0)),
            safety_flags=[str(flag) for flag in data.get("safety_flags", [])],
            reviewed_at=str(data.get("reviewed_at") or _utc_now()),
        )


@dataclass(frozen=True)
class EvolutionReviewBundle:
    """The auditable self-evolve chain for one source or removal."""

    instructions: list[EvolutionInstruction]
    proposals: list[PatchProposal]
    reviews: list[ReviewDecision]

    def to_dict(self) -> dict[str, Any]:
        return {
            "instructions": [instruction.to_dict() for instruction in self.instructions],
            "patch_proposals": [proposal.to_dict() for proposal in self.proposals],
            "review_decisions": [review.to_dict() for review in self.reviews],
        }


class SelfEvolveEngine:
    """Convert evidence-backed candidates into reviewed long-term context patches."""

    def __init__(self, review_config: EvolutionReviewConfig | None = None) -> None:
        self.review_config = review_config or EvolutionReviewConfig()

    def build_for_source(
        self,
        *,
        source: str,
        evidence_path: str,
        evidence_text: str,
        candidates: Sequence[Mapping[str, Any]],
        previous_entries: Sequence[Mapping[str, Any]] = (),
    ) -> EvolutionReviewBundle:
        source_kind = classify_evolution_source(source, evidence_text)
        instructions = self.extract_instructions(
            source=source,
            evidence_path=evidence_path,
            evidence_text=evidence_text,
            source_kind=source_kind,
            candidates=candidates,
            previous_entries=previous_entries,
        )
        return self._review_instructions(instructions)

    def build_for_removed_source(
        self,
        *,
        source: str,
        evidence_path: str,
        previous_entries: Sequence[Mapping[str, Any]],
    ) -> EvolutionReviewBundle:
        instructions: list[EvolutionInstruction] = []
        source_kind = classify_evolution_source(source, "")
        for entry in previous_entries:
            target = cast(EvolutionTarget, str(entry.get("bucket", "memory")))
            evidence = EvidenceRecord(
                source=source,
                evidence_path=evidence_path,
                source_kind=source_kind,
                attribution="Manifest entry generated from a source that is no longer present.",
                summary=_entry_summary(entry),
                conflicts=[],
            )
            content = {
                "entry_id": str(entry.get("id", "")),
                "previous_entry": dict(entry),
            }
            instructions.append(
                EvolutionInstruction(
                    id=_stable_id("evi", source, target, "delete", str(entry.get("id", ""))),
                    target=target,
                    operation="delete",
                    reason="Remove long-term context that was generated from a deleted raw source.",
                    evidence=evidence,
                    priority="medium",
                    confidence=1.0,
                    content=content,
                )
            )
        return self._review_instructions(instructions)

    def extract_instructions(
        self,
        *,
        source: str,
        evidence_path: str,
        evidence_text: str,
        source_kind: EvolutionSourceKind,
        candidates: Sequence[Mapping[str, Any]],
        previous_entries: Sequence[Mapping[str, Any]] = (),
    ) -> list[EvolutionInstruction]:
        previous_by_id = {str(entry.get("id", "")): dict(entry) for entry in previous_entries if entry.get("id")}
        candidate_ids: set[str] = set()
        instructions: list[EvolutionInstruction] = []

        for candidate in candidates:
            entry_id = str(candidate.get("id", ""))
            if not entry_id:
                continue
            candidate_ids.add(entry_id)
            operation: EvolutionOperation = "update" if entry_id in previous_by_id else "add"
            target = cast(EvolutionTarget, str(candidate.get("bucket", "memory")))
            conflicts = detect_evidence_conflicts(evidence_text)
            evidence = EvidenceRecord(
                source=source,
                evidence_path=evidence_path,
                source_kind=source_kind,
                attribution=self._attribution_for(source_kind, source),
                summary=_entry_summary(candidate),
                conflicts=conflicts,
            )
            content = {
                "entry": dict(candidate),
                "previous_entry": previous_by_id.get(entry_id),
            }
            instructions.append(
                EvolutionInstruction(
                    id=_stable_id("evi", source, target, operation, entry_id, _entry_summary(candidate)),
                    target=target,
                    operation=operation,
                    reason=self._reason_for(operation, target, source_kind),
                    evidence=evidence,
                    priority=self._priority_for(source_kind, conflicts, candidate),
                    confidence=confidence_score(candidate.get("confidence")),
                    content=content,
                )
            )

        for entry_id, previous in previous_by_id.items():
            if entry_id in candidate_ids:
                continue
            target = cast(EvolutionTarget, str(previous.get("bucket", "memory")))
            evidence = EvidenceRecord(
                source=source,
                evidence_path=evidence_path,
                source_kind=source_kind,
                attribution=self._attribution_for(source_kind, source),
                summary=_entry_summary(previous),
                conflicts=[],
            )
            instructions.append(
                EvolutionInstruction(
                    id=_stable_id("evi", source, target, "delete", entry_id),
                    target=target,
                    operation="delete",
                    reason="Remove stale generated context that is no longer supported by current evidence.",
                    evidence=evidence,
                    priority="medium",
                    confidence=1.0,
                    content={
                        "entry_id": entry_id,
                        "previous_entry": dict(previous),
                    },
                )
            )

        return instructions

    def _review_instructions(self, instructions: Sequence[EvolutionInstruction]) -> EvolutionReviewBundle:
        proposals = [self.build_patch_proposal(instruction) for instruction in instructions]
        reviews = [self.review_patch_proposal(proposal) for proposal in proposals]
        return EvolutionReviewBundle(instructions=list(instructions), proposals=proposals, reviews=reviews)

    def build_patch_proposal(self, instruction: EvolutionInstruction) -> PatchProposal:
        target_path = f"{instruction.target}.md"
        entry = instruction.content.get("entry")
        entry_id = instruction.content.get("entry_id")
        if instruction.operation in {"add", "update"} and isinstance(entry, Mapping):
            patch: dict[str, Any] = {"entry": dict(entry)}
            summary = _entry_summary(entry)
        else:
            patch = {"entry_id": str(entry_id or "")}
            summary = f"Remove generated entry {entry_id}"
        return PatchProposal(
            id=_stable_id("patch", instruction.id, instruction.operation, target_path),
            instruction_id=instruction.id,
            target=instruction.target,
            operation=instruction.operation,
            target_path=target_path,
            summary=summary,
            patch=patch,
            reason=instruction.reason,
            evidence=instruction.evidence,
            priority=instruction.priority,
            confidence=instruction.confidence,
        )

    def review_patch_proposal(self, proposal: PatchProposal) -> ReviewDecision:
        flags = self._safety_flags(proposal)
        if proposal.confidence < self.review_config.min_confidence:
            flags.append("below_min_confidence")
        if proposal.evidence.conflicts and self.review_config.require_conflict_review:
            flags.append("conflict_detected")

        if not self.review_config.auto_approve:
            return ReviewDecision(
                proposal_id=proposal.id,
                status="needs_review",
                reviewer="creator",
                reason="Creator review is required before this patch can update long-term context.",
                confidence=proposal.confidence,
                safety_flags=flags,
            )
        if flags:
            return ReviewDecision(
                proposal_id=proposal.id,
                status="needs_review",
                reviewer="auto-review",
                reason="Patch requires review because one or more safety checks did not pass.",
                confidence=proposal.confidence,
                safety_flags=flags,
            )
        return ReviewDecision(
            proposal_id=proposal.id,
            status="approved",
            reviewer="auto-review",
            reason="Patch passed traceability, confidence, and safety checks.",
            confidence=proposal.confidence,
            safety_flags=[],
        )

    def _safety_flags(self, proposal: PatchProposal) -> list[str]:
        flags: list[str] = []
        if proposal.target not in {"memory", "soul", "skill"}:
            flags.append("invalid_target")
        if proposal.operation not in {"add", "update", "delete"}:
            flags.append("invalid_operation")
        if self.review_config.require_traceable_evidence:
            if not proposal.evidence.source:
                flags.append("missing_evidence_source")
            if not proposal.evidence.evidence_path:
                flags.append("missing_evidence_path")
        if proposal.operation in {"add", "update"} and not isinstance(proposal.patch.get("entry"), Mapping):
            flags.append("missing_patch_entry")
        if proposal.operation == "delete" and not proposal.patch.get("entry_id"):
            flags.append("missing_delete_entry_id")
        return flags

    def _attribution_for(self, source_kind: EvolutionSourceKind, source: str) -> str:
        if source_kind == "agent_log":
            return f"Agent execution evidence from {source}."
        if source_kind == "creator_feedback":
            return f"Creator-authored feedback from {source}."
        if source_kind == "observation":
            return f"New observation evidence from {source}."
        if source_kind == "user_upload":
            return f"User-uploaded evidence from {source}."
        return f"Evidence from {source}."

    def _reason_for(
        self,
        operation: EvolutionOperation,
        target: EvolutionTarget,
        source_kind: EvolutionSourceKind,
    ) -> str:
        source_phrase = source_kind.replace("_", " ")
        if operation == "delete":
            return f"Delete stale {target} context because the source evidence no longer supports it."
        if operation == "update":
            return f"Update {target} context using structured evidence extracted from {source_phrase}."
        return f"Add {target} context using structured evidence extracted from {source_phrase}."

    def _priority_for(
        self,
        source_kind: EvolutionSourceKind,
        conflicts: Sequence[str],
        candidate: Mapping[str, Any],
    ) -> EvolutionPriority:
        if conflicts or source_kind == "creator_feedback":
            return "high"
        if str(candidate.get("bucket", "")) == "skill" or source_kind == "agent_log":
            return "medium"
        return "low"


def apply_reviewed_proposals(
    previous_entries: Sequence[Mapping[str, Any]],
    proposals: Sequence[PatchProposal],
    reviews: Sequence[ReviewDecision],
) -> list[dict[str, Any]]:
    """Apply only approved proposals to a source's existing generated entries."""

    entries_by_id = {str(entry.get("id", "")): dict(entry) for entry in previous_entries if entry.get("id")}
    order = [str(entry.get("id", "")) for entry in previous_entries if entry.get("id")]
    review_by_proposal = {review.proposal_id: review for review in reviews}
    for proposal in proposals:
        review = review_by_proposal.get(proposal.id)
        if review is None or not review.approved:
            continue
        if proposal.operation in {"add", "update"}:
            entry = proposal.patch.get("entry")
            if not isinstance(entry, Mapping):
                continue
            entry_id = str(entry.get("id", ""))
            if not entry_id:
                continue
            entries_by_id[entry_id] = dict(entry)
            if entry_id not in order:
                order.append(entry_id)
        elif proposal.operation == "delete":
            entry_id = str(proposal.patch.get("entry_id", ""))
            entries_by_id.pop(entry_id, None)
            order = [item for item in order if item != entry_id]
    return [entries_by_id[entry_id] for entry_id in order if entry_id in entries_by_id]


def classify_evolution_source(source: str, evidence_text: str) -> EvolutionSourceKind:
    lowered_source = source.lower()
    lowered_evidence = evidence_text.lower()
    if "skill_traces/" in lowered_source or "agent_log" in lowered_source or "agent-log" in lowered_source:
        return "agent_log"
    if "skill evolution trace" in lowered_evidence:
        return "agent_log"
    if "creator" in lowered_source or "feedback" in lowered_source:
        return "creator_feedback"
    if "observation" in lowered_source or "new_observation" in lowered_source:
        return "observation"
    if source:
        return "user_upload"
    return "unknown"


def detect_evidence_conflicts(evidence_text: str) -> list[str]:
    lowered = evidence_text.lower()
    markers = (
        "conflict",
        "contradict",
        "correction",
        "instead of",
        "replace previous",
        "actually",
    )
    if any(marker in lowered for marker in markers):
        return ["Evidence contains language that may conflict with existing long-term context."]
    return []


def confidence_score(value: Any) -> float:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return max(0.0, min(float(value), 1.0))
    lowered = str(value or "").strip().lower()
    if lowered == "high":
        return 0.9
    if lowered == "medium":
        return 0.65
    if lowered == "low":
        return 0.35
    return 0.5


def write_evolution_audit(
    metadata_dir: str | Path,
    *,
    instructions: Sequence[EvolutionInstruction],
    proposals: Sequence[PatchProposal],
    reviews: Sequence[ReviewDecision],
) -> None:
    if not instructions and not proposals and not reviews:
        return
    evolution_dir = Path(metadata_dir) / "evolution"
    evolution_dir.mkdir(parents=True, exist_ok=True)
    _append_jsonl(evolution_dir / "instructions.jsonl", [instruction.to_dict() for instruction in instructions])
    _append_jsonl(evolution_dir / "patch_proposals.jsonl", [proposal.to_dict() for proposal in proposals])
    _append_jsonl(evolution_dir / "review_decisions.jsonl", [review.to_dict() for review in reviews])
    latest = {
        "updated_at": _utc_now(),
        "instructions": [instruction.to_dict() for instruction in instructions],
        "patch_proposals": [proposal.to_dict() for proposal in proposals],
        "review_decisions": [review.to_dict() for review in reviews],
    }
    (evolution_dir / "latest.json").write_text(
        json.dumps(latest, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def _append_jsonl(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    if not records:
        return
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def _entry_summary(entry: Mapping[str, Any]) -> str:
    title = str(entry.get("title", "")).strip()
    body = str(entry.get("body", "")).strip()
    summary = title or body
    if "\n" in summary:
        summary = summary.splitlines()[0].strip()
    if len(summary) > 180:
        return summary[:177].rstrip() + "..."
    return summary


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(str(part).encode("utf-8"))
        digest.update(b"\0")
    return f"{prefix}_{digest.hexdigest()[:16]}"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "EvidenceRecord",
    "EvolutionInstruction",
    "EvolutionOperation",
    "EvolutionPriority",
    "EvolutionReviewBundle",
    "EvolutionReviewConfig",
    "EvolutionSourceKind",
    "EvolutionTarget",
    "PatchProposal",
    "ReviewDecision",
    "ReviewStatus",
    "SelfEvolveEngine",
    "apply_reviewed_proposals",
    "classify_evolution_source",
    "confidence_score",
    "detect_evidence_conflicts",
    "write_evolution_audit",
]
