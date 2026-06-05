from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

from memu.app.folder import GENERATED_END, GENERATED_START


SkillTraceOutcome = Literal["success", "failure", "partial", "unknown"]


@dataclass(frozen=True)
class SkillToolTrace:
    name: str
    input: str = ""
    output: str = ""
    success: bool = True
    score: float | None = None


@dataclass(frozen=True)
class SkillTrace:
    task: str
    outcome: SkillTraceOutcome = "unknown"
    summary: str = ""
    actions: list[str] = field(default_factory=list)
    tools: list[SkillToolTrace] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z"))

    def to_markdown(self) -> str:
        lines = [
            "# Skill Evolution Trace",
            "",
            "This raw trace is evidence for self-evolving skills. It captures what was attempted, "
            "which tools or workflows were used, what happened, and what should be reused next time.",
            "",
            "## Metadata",
            "",
            f"- created_at: {self.created_at}",
            f"- outcome: {self.outcome}",
            f"- task: {self.task}",
        ]
        for key, value in sorted(self.metadata.items()):
            lines.append(f"- {key}: {value}")

        lines.extend(["", "## Summary", "", self.summary or "No summary provided."])

        lines.extend(["", "## Actions", ""])
        if self.actions:
            lines.extend(f"{idx}. {action}" for idx, action in enumerate(self.actions, start=1))
        else:
            lines.append("No actions recorded.")

        lines.extend(["", "## Tool Calls", ""])
        if self.tools:
            for idx, tool in enumerate(self.tools, start=1):
                lines.extend(
                    [
                        f"{idx}. Tool: {tool.name}",
                        f"   - success: {tool.success}",
                    ]
                )
                if tool.score is not None:
                    lines.append(f"   - score: {tool.score}")
                if tool.input:
                    lines.append(f"   - input: {tool.input}")
                if tool.output:
                    lines.append(f"   - output: {tool.output}")
        else:
            lines.append("No tool calls recorded.")

        lines.extend(["", "## Lessons For Skill Evolution", ""])
        if self.lessons:
            lines.extend(f"- Skill: {lesson}" for lesson in self.lessons)
        else:
            lines.append("- Skill: No explicit lesson recorded; review the task and outcome before reusing.")

        lines.extend(
            [
                "",
                "## Retrieval Hints",
                "",
                "- when_to_use: Retrieve this skill trace for similar tasks, tools, workflows, or failure modes.",
                "- memory_bucket: skill",
                "- evidence_type: skill_trace",
                "",
            ]
        )
        return "\n".join(lines)


@dataclass(frozen=True)
class SkillTraceRecord:
    raw_data_dir: Path
    trace_path: Path
    trace: SkillTrace


@dataclass(frozen=True)
class SkillPromotionRecord:
    repo_dir: Path
    skill_path: Path
    card_path: Path | None
    title: str
    promoted_at: str
    content: str


@dataclass(frozen=True)
class SkillEvolutionProposal:
    """A deterministic candidate skill distilled from raw skill traces."""

    title: str
    when_to_use: str
    lessons: list[str]
    actions: list[str]
    tools: list[str]
    sources: list[str]
    outcomes: dict[SkillTraceOutcome, int]
    support_count: int
    score: float
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "when_to_use": self.when_to_use,
            "lessons": list(self.lessons),
            "actions": list(self.actions),
            "tools": list(self.tools),
            "sources": list(self.sources),
            "outcomes": dict(self.outcomes),
            "support_count": self.support_count,
            "score": self.score,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }

    def to_promotion_kwargs(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "lessons": list(self.lessons),
            "actions": list(self.actions),
            "when_to_use": self.when_to_use,
            "source": ", ".join(self.sources),
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }


def record_skill_trace(
    raw_data_dir: str | Path,
    *,
    task: str,
    outcome: SkillTraceOutcome = "unknown",
    summary: str = "",
    actions: list[str] | None = None,
    tools: list[SkillToolTrace] | None = None,
    lessons: list[str] | None = None,
    metadata: dict[str, str] | None = None,
) -> SkillTraceRecord:
    raw_dir = Path(raw_data_dir).resolve()
    raw_dir.mkdir(parents=True, exist_ok=True)
    trace = SkillTrace(
        task=task,
        outcome=outcome,
        summary=summary,
        actions=list(actions or []),
        tools=list(tools or []),
        lessons=list(lessons or []),
        metadata=dict(metadata or {}),
    )
    trace_dir = raw_dir / "skill_traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    trace_path = trace_dir / _trace_filename(trace)
    trace_path.write_text(trace.to_markdown(), encoding="utf-8")
    return SkillTraceRecord(raw_data_dir=raw_dir, trace_path=trace_path, trace=trace)


def suggest_skill_promotions(
    raw_data_dir: str | Path,
    *,
    limit: int = 5,
    min_support: int = 1,
) -> list[SkillEvolutionProposal]:
    """Suggest durable skill promotions from raw skill evolution traces."""

    if limit <= 0:
        msg = "limit must be greater than 0"
        raise ValueError(msg)
    if min_support <= 0:
        msg = "min_support must be greater than 0"
        raise ValueError(msg)

    raw_dir = Path(raw_data_dir).resolve()
    trace_dir = raw_dir / "skill_traces"
    if not trace_dir.exists() or not trace_dir.is_dir():
        return []

    groups: dict[str, dict[str, Any]] = {}
    for trace_path in sorted(trace_dir.rglob("*.md")):
        trace = _parse_skill_trace(trace_path, raw_dir)
        if trace is None:
            continue
        title = _proposal_title(trace)
        key = _slug(title) or hashlib.sha256(title.encode("utf-8")).hexdigest()[:10]
        group = groups.setdefault(
            key,
            {
                "title": title,
                "tasks": [],
                "lessons": [],
                "actions": [],
                "tools": [],
                "sources": [],
                "outcomes": {},
            },
        )
        group["tasks"].append(trace["task"])
        group["lessons"] = _merge_unique(group["lessons"], trace["lessons"])
        group["actions"] = _merge_unique(group["actions"], trace["actions"])
        group["tools"] = _merge_unique(group["tools"], trace["tools"])
        group["sources"] = _merge_unique(group["sources"], [trace["source"]])
        outcomes = cast(dict[SkillTraceOutcome, int], group["outcomes"])
        outcome = cast(SkillTraceOutcome, trace["outcome"])
        outcomes[outcome] = outcomes.get(outcome, 0) + 1

    proposals: list[SkillEvolutionProposal] = []
    for group in groups.values():
        sources = cast(list[str], group["sources"])
        support_count = len(sources)
        if support_count < min_support:
            continue
        outcomes = cast(dict[SkillTraceOutcome, int], group["outcomes"])
        title = str(group["title"])
        lessons = cast(list[str], group["lessons"])
        actions = cast(list[str], group["actions"])
        tools = cast(list[str], group["tools"])
        tasks = cast(list[str], group["tasks"])
        score = _proposal_score(support_count, outcomes, lessons, actions, tools)
        proposals.append(
            SkillEvolutionProposal(
                title=title,
                when_to_use=_proposal_when_to_use(title, tasks),
                lessons=lessons,
                actions=actions,
                tools=tools,
                sources=sources,
                outcomes=outcomes,
                support_count=support_count,
                score=score,
                tags=_proposal_tags(tools),
                metadata={
                    "suggested_by": "memu-skill-evolution",
                    "support_count": str(support_count),
                    "score": f"{score:.2f}",
                },
            )
        )
    return sorted(proposals, key=lambda item: (-item.score, -item.support_count, item.title.lower()))[:limit]


def promote_skill(
    repo_dir: str | Path,
    *,
    title: str,
    lessons: list[str] | None = None,
    actions: list[str] | None = None,
    when_to_use: str = "",
    source: str = "",
    tags: list[str] | None = None,
    metadata: dict[str, str] | None = None,
) -> SkillPromotionRecord:
    repo = Path(repo_dir).resolve()
    repo.mkdir(parents=True, exist_ok=True)
    skill_path = repo / "skill.md"
    clean_title = title.strip() or "Untitled Skill"
    card_path = repo / "skill" / "promoted" / f"{_slug(clean_title) or 'promoted-skill'}.md"
    existing = _read_existing_promotion(card_path)
    promoted_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    merged_lessons = _merge_unique(existing.get("lessons", []), list(lessons or []))
    merged_actions = _merge_unique(existing.get("actions", []), list(actions or []))
    merged_tags = _merge_unique(existing.get("tags", []), list(tags or []))
    existing_when_to_use = existing.get("when_to_use", "")
    if not isinstance(existing_when_to_use, str):
        existing_when_to_use = ""
    merged_when_to_use = when_to_use or existing_when_to_use
    existing_source = existing.get("source", "")
    if not isinstance(existing_source, str):
        existing_source = ""
    merged_source = source or existing_source
    existing_metadata = existing.get("metadata", {})
    if not isinstance(existing_metadata, dict):
        existing_metadata = {}
    merged_metadata = {str(key): str(value) for key, value in existing_metadata.items()}
    merged_metadata.update(dict(metadata or {}))
    content = _promotion_markdown(
        title=title,
        promoted_at=promoted_at,
        lessons=merged_lessons,
        actions=merged_actions,
        when_to_use=merged_when_to_use,
        source=merged_source,
        tags=merged_tags,
        metadata=merged_metadata,
        heading_level=1,
    )
    index_content = _promotion_index_markdown(
        title=clean_title,
        promoted_at=promoted_at,
        card_rel_path=card_path.relative_to(repo).as_posix(),
        when_to_use=merged_when_to_use,
        source=merged_source,
        tags=merged_tags,
        metadata=merged_metadata,
    )
    _ensure_skill_file(skill_path)
    current = skill_path.read_text(encoding="utf-8-sig")
    skill_path.write_text(_upsert_promoted_section(current, clean_title, index_content), encoding="utf-8")
    card_path.parent.mkdir(parents=True, exist_ok=True)
    card_path.write_text(content, encoding="utf-8")
    return SkillPromotionRecord(
        repo_dir=repo,
        skill_path=skill_path,
        card_path=card_path,
        title=title,
        promoted_at=promoted_at,
        content=content,
    )


def _parse_skill_trace(trace_path: Path, raw_dir: Path) -> dict[str, Any] | None:
    try:
        markdown = trace_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return None
    if "Skill Evolution Trace" not in markdown:
        return None
    metadata = _trace_metadata(markdown)
    task = metadata.get("task", "").strip()
    outcome = metadata.get("outcome", "unknown").strip()
    if outcome not in {"success", "failure", "partial", "unknown"}:
        outcome = "unknown"
    lessons = _trace_lessons(markdown)
    actions = _trace_actions(markdown)
    tools = _trace_tools(markdown)
    if not task and not lessons:
        return None
    return {
        "task": task or "Untitled skill trace",
        "outcome": outcome,
        "lessons": lessons,
        "actions": actions,
        "tools": tools,
        "source": trace_path.relative_to(raw_dir).as_posix(),
    }


def _trace_metadata(markdown: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in _extract_h2_section(markdown, "Metadata").splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key, _, value = stripped[2:].partition(":")
        metadata[key.strip()] = value.strip()
    return metadata


def _trace_lessons(markdown: str) -> list[str]:
    lessons: list[str] = []
    for line in _extract_h2_section(markdown, "Lessons For Skill Evolution").splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        lesson = stripped[2:].strip()
        if lesson.lower().startswith("skill:"):
            lesson = lesson.partition(":")[2].strip()
        if lesson and not lesson.lower().startswith("no explicit lesson recorded"):
            lessons.append(lesson)
    return _merge_unique([], lessons)


def _trace_actions(markdown: str) -> list[str]:
    actions: list[str] = []
    for line in _extract_h2_section(markdown, "Actions").splitlines():
        stripped = line.strip()
        marker = stripped.partition(". ")
        if marker[0].isdigit() and marker[2]:
            actions.append(marker[2].strip())
    return _merge_unique([], actions)


def _trace_tools(markdown: str) -> list[str]:
    tools: list[str] = []
    for line in _extract_h2_section(markdown, "Tool Calls").splitlines():
        stripped = line.strip()
        match = re.match(r"\d+\.\s+Tool:\s+(.+)", stripped)
        if match:
            tools.append(match.group(1).strip())
    return _merge_unique([], tools)


def _extract_h2_section(markdown: str, heading: str) -> str:
    lines = markdown.splitlines()
    start: int | None = None
    target = f"## {heading}".lower()
    for idx, line in enumerate(lines):
        if line.strip().lower() == target:
            start = idx + 1
            break
    if start is None:
        return ""
    end = start
    while end < len(lines):
        if lines[end].startswith("## "):
            break
        end += 1
    return "\n".join(lines[start:end]).strip()


def _proposal_title(trace: dict[str, Any]) -> str:
    lessons = cast(list[str], trace["lessons"])
    base = lessons[0] if lessons else str(trace["task"])
    base = base.strip().rstrip(".")
    base = re.split(r"\s+(before|after|when|while|so that|for)\s+", base, maxsplit=1, flags=re.IGNORECASE)[0]
    words = re.findall(r"[A-Za-z0-9]+", base)
    if words:
        return " ".join(word.capitalize() for word in words[:6])
    return base[:48] or "Untitled Skill"


def _proposal_when_to_use(title: str, tasks: list[str]) -> str:
    task = next((item for item in tasks if item), "")
    if task:
        return f"Use when a future task resembles: {task}"
    return f"Use when a future task requires {title.lower()}."


def _proposal_score(
    support_count: int,
    outcomes: dict[SkillTraceOutcome, int],
    lessons: list[str],
    actions: list[str],
    tools: list[str],
) -> float:
    total = max(sum(outcomes.values()), 1)
    success_weight = outcomes.get("success", 0) / total
    partial_weight = outcomes.get("partial", 0) / total
    return round(
        support_count + success_weight + (partial_weight * 0.5) + (len(lessons) * 0.1) + (len(actions) * 0.05)
        + (len(tools) * 0.05),
        2,
    )


def _proposal_tags(tools: list[str]) -> list[str]:
    tags = ["suggested", "skill-evolution"]
    for tool in tools[:3]:
        slug = _slug(tool)
        if slug:
            tags.append(slug)
    return _merge_unique([], tags)


def _promotion_markdown(
    *,
    title: str,
    promoted_at: str,
    lessons: list[str],
    actions: list[str],
    when_to_use: str,
    source: str,
    tags: list[str],
    metadata: dict[str, str],
    heading_level: int = 2,
) -> str:
    clean_title = title.strip() or "Untitled Skill"
    heading = "#" * heading_level
    lines = [
        f"{heading} Promoted Skill: {clean_title}",
        "",
        f"- promoted_at: {promoted_at}",
    ]
    if source:
        lines.append(f"- source: {source}")
    if tags:
        lines.append(f"- tags: {', '.join(tags)}")
    for key, value in sorted(metadata.items()):
        lines.append(f"- {key}: {value}")

    lines.extend(["", "### When To Use", "", when_to_use or "Use when a future task matches this skill pattern."])
    lines.extend(["", "### Procedure", ""])
    if actions:
        lines.extend(f"{idx}. {action}" for idx, action in enumerate(actions, start=1))
    else:
        lines.append("1. Review the task context and apply the promoted lesson deliberately.")

    lines.extend(["", "### Lessons", ""])
    if lessons:
        lines.extend(f"- {lesson}" for lesson in lessons)
    else:
        lines.append("- Reuse this skill when the same workflow or failure mode appears.")
    lines.append("")
    return "\n".join(lines)


def _promotion_index_markdown(
    *,
    title: str,
    promoted_at: str,
    card_rel_path: str,
    when_to_use: str,
    source: str,
    tags: list[str],
    metadata: dict[str, str],
) -> str:
    lines = [
        f"## Promoted Skill: {title}",
        "",
        f"- promoted_at: {promoted_at}",
        f"- card: {card_rel_path}",
    ]
    if source:
        lines.append(f"- source: {source}")
    if tags:
        lines.append(f"- tags: {', '.join(tags)}")
    for key, value in sorted(metadata.items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", when_to_use or "Use when a future task matches this skill pattern.", ""])
    return "\n".join(lines)


def _upsert_promoted_section(current: str, title: str, section: str) -> str:
    lines = current.rstrip().splitlines()
    start = _find_promoted_section_start(lines, title)
    if start is None:
        return current.rstrip() + "\n\n" + section
    end = start + 1
    while end < len(lines):
        if lines[end].startswith("## "):
            break
        end += 1
    updated = lines[:start] + section.rstrip().splitlines() + lines[end:]
    return "\n".join(updated).rstrip() + "\n"


def _find_promoted_section_start(lines: list[str], title: str) -> int | None:
    target = f"## Promoted Skill: {title}".strip().lower()
    for idx, line in enumerate(lines):
        if line.strip().lower() == target:
            return idx
    return None


def _read_existing_promotion(card_path: Path) -> dict[str, Any]:
    if not card_path.exists():
        return {}
    try:
        current = card_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return {}
    return {
        "actions": _extract_numbered_section(current, "Procedure"),
        "lessons": _extract_bullet_section(current, "Lessons"),
        "tags": _extract_metadata_list(current, "tags"),
        "when_to_use": _extract_text_section(current, "When To Use"),
        "source": _extract_metadata_value(current, "source"),
        "metadata": _extract_promotion_metadata(current),
    }


def _extract_numbered_section(markdown: str, heading: str) -> list[str]:
    section = _extract_section(markdown, heading)
    values: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        marker = stripped.partition(". ")
        if marker[0].isdigit() and marker[2]:
            values.append(marker[2].strip())
    return values


def _extract_bullet_section(markdown: str, heading: str) -> list[str]:
    section = _extract_section(markdown, heading)
    values: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            values.append(stripped[2:].strip())
    return values


def _extract_text_section(markdown: str, heading: str) -> str:
    lines = [line.strip() for line in _extract_section(markdown, heading).splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _extract_section(markdown: str, heading: str) -> str:
    lines = markdown.splitlines()
    start: int | None = None
    for idx, line in enumerate(lines):
        if line.strip().lower() == f"### {heading}".lower():
            start = idx + 1
            break
    if start is None:
        return ""
    end = start
    while end < len(lines):
        if lines[end].startswith("### ") or lines[end].startswith("## "):
            break
        end += 1
    return "\n".join(lines[start:end]).strip()


def _extract_metadata_list(markdown: str, key: str) -> list[str]:
    prefix = f"- {key}:"
    for line in markdown.splitlines():
        if line.lower().startswith(prefix.lower()):
            return [part.strip() for part in line.partition(":")[2].split(",") if part.strip()]
    return []


def _extract_metadata_value(markdown: str, key: str) -> str:
    prefix = f"- {key}:"
    for line in markdown.splitlines():
        if line.lower().startswith(prefix.lower()):
            return line.partition(":")[2].strip()
    return ""


def _extract_promotion_metadata(markdown: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    reserved = {"promoted_at", "source", "tags", "card"}
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("### "):
            break
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key, _, value = stripped[2:].partition(":")
        clean_key = key.strip()
        if clean_key and clean_key not in reserved:
            metadata[clean_key] = value.strip()
    return metadata


def _merge_unique(existing: list[str] | str | object, incoming: list[str]) -> list[str]:
    values = existing if isinstance(existing, list) else []
    merged: list[str] = []
    seen: set[str] = set()
    for value in [*values, *incoming]:
        clean = str(value).strip()
        key = clean.lower()
        if clean and key not in seen:
            merged.append(clean)
            seen.add(key)
    return merged


def _ensure_skill_file(skill_path: Path) -> None:
    if skill_path.exists():
        return
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(
        f"# Skill\n\n{GENERATED_START}\nNo generated entries yet.\n{GENERATED_END}\n",
        encoding="utf-8",
    )


def _trace_filename(trace: SkillTrace) -> str:
    slug = _slug(trace.task) or "skill-trace"
    digest = hashlib.sha256(trace.to_markdown().encode("utf-8")).hexdigest()[:10]
    timestamp = trace.created_at.replace(":", "").replace("-", "").replace(".", "")
    timestamp = timestamp.replace("Z", "z")
    return f"{timestamp}_{slug}_{digest}.md"


def _slug(value: str) -> str:
    lowered = value.lower()
    chars: list[str] = []
    previous_dash = False
    for char in lowered:
        if char.isalnum():
            chars.append(char)
            previous_dash = False
        elif not previous_dash:
            chars.append("-")
            previous_dash = True
    return "".join(chars).strip("-")[:80]


__all__ = [
    "SkillEvolutionProposal",
    "SkillPromotionRecord",
    "SkillToolTrace",
    "SkillTrace",
    "SkillTraceOutcome",
    "SkillTraceRecord",
    "promote_skill",
    "record_skill_trace",
    "suggest_skill_promotions",
]
