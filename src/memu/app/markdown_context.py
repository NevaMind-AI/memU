from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

from memu.app.folder import GENERATED_END, GENERATED_START


ContextBucket = Literal["memory", "soul", "skill"]
ContextSectionKind = Literal["generated", "manual"]


@dataclass(frozen=True)
class MarkdownContextSection:
    id: str
    bucket: ContextBucket
    title: str
    content: str
    source: str | None = None
    evidence: str | None = None
    tags: list[str] = field(default_factory=list)
    kind: ContextSectionKind = "generated"
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "bucket": self.bucket,
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "evidence": self.evidence,
            "tags": list(self.tags),
            "kind": self.kind,
            "score": self.score,
        }


@dataclass(frozen=True)
class MarkdownContextPack:
    repo_dir: Path
    query: str | None
    max_chars: int
    used_chars: int
    sections: list[MarkdownContextSection]
    omitted_count: int = 0
    bucket_char_limits: dict[ContextBucket, int] = field(default_factory=dict)
    used_chars_by_bucket: dict[ContextBucket, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_dir": str(self.repo_dir),
            "query": self.query,
            "max_chars": self.max_chars,
            "used_chars": self.used_chars,
            "bucket_char_limits": dict(self.bucket_char_limits),
            "used_chars_by_bucket": dict(self.used_chars_by_bucket),
            "omitted_count": self.omitted_count,
            "sections": [section.to_dict() for section in self.sections],
        }

    def to_summary(self) -> dict[str, Any]:
        buckets = {bucket: 0 for bucket in ("memory", "soul", "skill")}
        kinds = {kind: 0 for kind in ("generated", "manual")}
        sources: set[str] = set()
        section_summaries: list[dict[str, Any]] = []
        for section in self.sections:
            buckets[section.bucket] += 1
            kinds[section.kind] += 1
            if section.source:
                sources.add(section.source)
            section_summaries.append(
                {
                    "id": section.id,
                    "bucket": section.bucket,
                    "kind": section.kind,
                    "title": section.title,
                    "source": section.source,
                    "evidence": section.evidence,
                    "tags": list(section.tags),
                    "score": section.score,
                }
            )
        return {
            "repo_dir": str(self.repo_dir),
            "query": self.query,
            "max_chars": self.max_chars,
            "used_chars": self.used_chars,
            "bucket_char_limits": dict(self.bucket_char_limits),
            "used_chars_by_bucket": dict(self.used_chars_by_bucket),
            "omitted_count": self.omitted_count,
            "section_count": len(self.sections),
            "buckets": buckets,
            "kinds": kinds,
            "sources": sorted(sources),
            "sections": section_summaries,
        }

    def to_markdown(self) -> str:
        lines = ["<memu_context>"]
        if self.query:
            lines.extend(["", f"Query: {self.query}"])
        for section in self.sections:
            lines.extend(
                [
                    "",
                    f"## {section.bucket}: {section.title}",
                    "",
                    f"- id: {section.id}",
                    f"- kind: {section.kind}",
                ]
            )
            if section.source:
                lines.append(f"- source: {section.source}")
            if section.evidence:
                lines.append(f"- evidence: {section.evidence}")
            if section.tags:
                lines.append(f"- tags: {', '.join(section.tags)}")
            lines.extend(["", section.content.strip()])
        if self.omitted_count:
            lines.extend(["", f"[{self.omitted_count} section(s) omitted by context budget]"])
        lines.extend(["", "</memu_context>"])
        return "\n".join(lines).strip() + "\n"

    def to_system_prompt(self) -> str:
        return _CONTEXT_SYSTEM_INSTRUCTIONS + "\n\n" + self.to_markdown()

    def to_messages(self) -> list[dict[str, str]]:
        return [{"role": "system", "content": self.to_system_prompt()}]

    def inject_into_messages(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        replace_existing: bool = True,
    ) -> list[dict[str, Any]]:
        return inject_context_messages(messages, self, replace_existing=replace_existing)


class MarkdownMemoryRepository:
    """Read a Markdown-backed memU repository and assemble context packs."""

    def __init__(self, repo_dir: str | Path):
        self.repo_dir = Path(repo_dir).resolve()

    def list_sections(
        self,
        *,
        buckets: Sequence[ContextBucket] | None = None,
        include_generated: bool = True,
        include_manual: bool = True,
    ) -> list[MarkdownContextSection]:
        requested = set(buckets or ("soul", "memory", "skill"))
        sections: list[MarkdownContextSection] = []
        if include_generated:
            sections.extend(section for section in self._load_generated_sections() if section.bucket in requested)
        if include_manual:
            sections.extend(section for section in self._load_manual_sections() if section.bucket in requested)
        return self._sort_sections(sections)

    def build_context_pack(
        self,
        *,
        query: str | None = None,
        buckets: Sequence[ContextBucket] | None = None,
        max_chars: int = 8000,
        include_generated: bool = True,
        include_manual: bool = True,
        bucket_char_limits: Mapping[ContextBucket, int] | None = None,
    ) -> MarkdownContextPack:
        candidates = self.list_sections(
            buckets=buckets,
            include_generated=include_generated,
            include_manual=include_manual,
        )
        ranked = self._rank_sections(candidates, query)
        limits = self._normalize_bucket_char_limits(bucket_char_limits)
        selected: list[MarkdownContextSection] = []
        used = 0
        used_by_bucket: dict[ContextBucket, int] = {}
        omitted = 0
        for section in ranked:
            rendered_len = self._section_char_cost(section)
            remaining = max_chars - used
            if section.bucket in limits:
                remaining = min(remaining, limits[section.bucket] - used_by_bucket.get(section.bucket, 0))
            if remaining <= 0:
                omitted += 1
                continue
            if rendered_len > remaining:
                if self._bucket_has_selected(selected, section.bucket):
                    omitted += 1
                    continue
                truncated = self._truncate_section(section, remaining)
                selected.append(truncated)
                rendered_len = self._section_char_cost(truncated)
                used += rendered_len
                used_by_bucket[section.bucket] = used_by_bucket.get(section.bucket, 0) + rendered_len
                continue
            selected.append(section)
            used += rendered_len
            used_by_bucket[section.bucket] = used_by_bucket.get(section.bucket, 0) + rendered_len
        return MarkdownContextPack(
            repo_dir=self.repo_dir,
            query=query,
            max_chars=max_chars,
            used_chars=used,
            sections=selected,
            omitted_count=omitted,
            bucket_char_limits=limits,
            used_chars_by_bucket=used_by_bucket,
        )

    def _load_generated_sections(self) -> list[MarkdownContextSection]:
        manifest_path = self.repo_dir / ".memu" / "manifest.json"
        if not manifest_path.exists():
            return []
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            return []
        sources = manifest.get("sources", {})
        if not isinstance(sources, Mapping):
            return []

        sections: list[MarkdownContextSection] = []
        for source in sources.values():
            if not isinstance(source, Mapping):
                continue
            for entry in source.get("entries", []):
                if not isinstance(entry, Mapping):
                    continue
                bucket = str(entry.get("bucket", "memory"))
                if bucket not in {"memory", "soul", "skill"}:
                    continue
                sections.append(
                    MarkdownContextSection(
                        id=str(entry.get("id", "")),
                        bucket=cast(ContextBucket, bucket),
                        title=str(entry.get("title", "")),
                        content=str(entry.get("body", "")).strip(),
                        source=str(entry.get("source")) if entry.get("source") else None,
                        evidence=str(entry.get("evidence")) if entry.get("evidence") else None,
                        tags=[str(tag) for tag in entry.get("tags", [])],
                        kind="generated",
                    )
                )
        return sections

    def _load_manual_sections(self) -> list[MarkdownContextSection]:
        sections: list[MarkdownContextSection] = []
        for bucket in ("soul", "memory", "skill"):
            paths = [self.repo_dir / f"{bucket}.md"]
            bucket_dir = self.repo_dir / bucket
            if bucket_dir.exists():
                paths.extend(sorted(bucket_dir.rglob("*.md")))
            for path in paths:
                if not path.exists() or not path.is_file():
                    continue
                manual = self._strip_generated_blocks(path.read_text(encoding="utf-8-sig")).strip()
                manual = self._strip_empty_title(manual, bucket)
                if bucket == "skill" and path == self.repo_dir / "skill.md":
                    manual = self._strip_promoted_skill_index_sections(manual)
                if not manual.strip():
                    continue
                rel_path = path.relative_to(self.repo_dir).as_posix()
                sections.append(
                    MarkdownContextSection(
                        id=f"manual:{rel_path}",
                        bucket=cast(ContextBucket, bucket),
                        title=f"Manual {bucket} notes from {rel_path}",
                        content=manual,
                        source=rel_path,
                        tags=["manual"],
                        kind="manual",
                    )
                )
        return sections

    def _rank_sections(
        self,
        sections: Sequence[MarkdownContextSection],
        query: str | None,
    ) -> list[MarkdownContextSection]:
        query_terms = self._terms(query or "")
        ranked: list[MarkdownContextSection] = []
        for section in sections:
            score = self._bucket_priority(section.bucket)
            if query_terms:
                haystack = " ".join([section.title, section.content, " ".join(section.tags)]).lower()
                score += sum(1.0 for term in query_terms if term in haystack)
            if section.kind == "manual":
                score += 0.25
            ranked.append(
                MarkdownContextSection(
                    id=section.id,
                    bucket=section.bucket,
                    title=section.title,
                    content=section.content,
                    source=section.source,
                    evidence=section.evidence,
                    tags=list(section.tags),
                    kind=section.kind,
                    score=score,
                )
            )
        return sorted(ranked, key=lambda item: (-item.score, self._bucket_sort_key(item.bucket), item.title))

    def _sort_sections(self, sections: Iterable[MarkdownContextSection]) -> list[MarkdownContextSection]:
        return sorted(sections, key=lambda item: (self._bucket_sort_key(item.bucket), item.kind, item.title))

    def _bucket_priority(self, bucket: ContextBucket) -> float:
        return {"soul": 3.0, "memory": 2.0, "skill": 1.0}[bucket]

    def _bucket_sort_key(self, bucket: ContextBucket) -> int:
        return {"soul": 0, "memory": 1, "skill": 2}[bucket]

    def _section_char_cost(self, section: MarkdownContextSection) -> int:
        return len(section.title) + len(section.content) + 160

    def _truncate_section(self, section: MarkdownContextSection, max_chars: int) -> MarkdownContextSection:
        budget = max(0, max_chars - len(section.title) - 200)
        content = section.content
        if len(content) > budget:
            content = content[:budget].rstrip() + "\n\n[truncated]"
        return MarkdownContextSection(
            id=section.id,
            bucket=section.bucket,
            title=section.title,
            content=content,
            source=section.source,
            evidence=section.evidence,
            tags=list(section.tags),
            kind=section.kind,
            score=section.score,
        )

    def _bucket_has_selected(
        self,
        sections: Sequence[MarkdownContextSection],
        bucket: ContextBucket,
    ) -> bool:
        return any(section.bucket == bucket for section in sections)

    def _normalize_bucket_char_limits(
        self,
        bucket_char_limits: Mapping[ContextBucket, int] | None,
    ) -> dict[ContextBucket, int]:
        if not bucket_char_limits:
            return {}
        normalized: dict[ContextBucket, int] = {}
        for bucket, limit in bucket_char_limits.items():
            if bucket not in {"memory", "soul", "skill"}:
                msg = f"unknown context bucket: {bucket}"
                raise ValueError(msg)
            if limit <= 0:
                msg = "bucket character limits must be greater than 0"
                raise ValueError(msg)
            normalized[cast(ContextBucket, bucket)] = int(limit)
        return normalized

    def _strip_generated_blocks(self, text: str) -> str:
        pattern = re.compile(
            rf"{re.escape(GENERATED_START)}.*?{re.escape(GENERATED_END)}",
            re.DOTALL,
        )
        return pattern.sub("", text)

    def _strip_empty_title(self, text: str, bucket: str) -> str:
        lines = text.splitlines()
        if not lines:
            return text
        first = lines[0].strip().lower()
        rest = "\n".join(lines[1:]).strip()
        generated_titles = {
            f"# {bucket}".lower(),
            f"# {bucket.title()}".lower(),
        }
        if first in generated_titles or first.startswith(f"# {bucket} from "):
            return rest
        if first.startswith("# ") and not rest:
            return ""
        return text

    def _strip_promoted_skill_index_sections(self, text: str) -> str:
        lines = text.splitlines()
        kept: list[str] = []
        idx = 0
        while idx < len(lines):
            line = lines[idx]
            if line.strip().lower().startswith("## promoted skill:"):
                end = idx + 1
                while end < len(lines) and not lines[end].startswith("## "):
                    end += 1
                section = "\n".join(lines[idx:end])
                card_path = self._promoted_card_path(section)
                if card_path is not None and card_path.is_file():
                    idx = end
                    continue
            kept.append(line)
            idx += 1
        return "\n".join(kept).strip()

    def _promoted_card_path(self, section: str) -> Path | None:
        for line in section.splitlines():
            stripped = line.strip()
            if not stripped.lower().startswith("- card:"):
                continue
            rel_path = stripped.partition(":")[2].strip()
            if not rel_path:
                return None
            card_path = (self.repo_dir / rel_path).resolve()
            try:
                card_path.relative_to(self.repo_dir)
            except ValueError:
                return None
            return card_path
        return None

    def _terms(self, query: str) -> set[str]:
        return {term.lower() for term in re.findall(r"[\w\u4e00-\u9fff]+", query) if len(term) >= 2}


def build_markdown_context_pack(
    repo_dir: str | Path,
    *,
    query: str | None = None,
    buckets: Sequence[ContextBucket] | None = None,
    max_chars: int = 8000,
    include_generated: bool = True,
    include_manual: bool = True,
    bucket_char_limits: Mapping[ContextBucket, int] | None = None,
) -> MarkdownContextPack:
    return MarkdownMemoryRepository(repo_dir).build_context_pack(
        query=query,
        buckets=buckets,
        max_chars=max_chars,
        include_generated=include_generated,
        include_manual=include_manual,
        bucket_char_limits=bucket_char_limits,
    )


def inject_context_messages(
    messages: Sequence[Mapping[str, Any]],
    context_pack: MarkdownContextPack,
    *,
    replace_existing: bool = True,
) -> list[dict[str, Any]]:
    injected = [dict(message) for message in messages]
    context = context_pack.to_system_prompt()
    if injected and injected[0].get("role") == "system" and isinstance(injected[0].get("content"), str):
        base_content = str(injected[0]["content"])
        if replace_existing:
            base_content = _strip_memu_context(base_content)
        injected[0]["content"] = _join_system_context(base_content, context)
        return injected
    injected.insert(0, {"role": "system", "content": context})
    return injected


def _strip_memu_context(content: str) -> str:
    for tag in ("memu_context_instructions", "memu_context"):
        content = re.sub(
            rf"\s*<{tag}>.*?</{tag}>\s*",
            "\n",
            content,
            flags=re.DOTALL,
        )
    return content.strip()


def _join_system_context(base_content: str, context: str) -> str:
    if not base_content.strip():
        return context
    return base_content.rstrip() + "\n\n" + context


__all__ = [
    "ContextBucket",
    "MarkdownContextPack",
    "MarkdownContextSection",
    "MarkdownMemoryRepository",
    "build_markdown_context_pack",
    "inject_context_messages",
]


_CONTEXT_SYSTEM_INSTRUCTIONS = """<memu_context_instructions>
Use the memU context below as retrieved working memory for the current task.
- Prefer manual sections when they conflict with generated sections.
- Use soul sections for persona, tone, language style, and interaction style.
- Use skill sections for reusable procedures, tool habits, and lessons learned.
- Use memory sections for durable facts, preferences, events, and knowledge.
- Treat generated sections as evidence-backed summaries; inspect source/evidence paths when the task needs precision.
- Do not invent facts beyond the context. If evidence is weak or conflicting, say what is uncertain.
</memu_context_instructions>"""
