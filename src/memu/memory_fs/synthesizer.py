"""LLM synthesis of MEMORY/SKILL artifacts from the shared description trunk.

This is the optional, opt-in counterpart to the deterministic exporter: instead of
rendering already-extracted database items/summaries, it feeds the per-source
multimodal descriptions to an LLM and synthesizes the memory document and skill
docs directly. ``INDEX.md`` stays deterministic and is handled by the exporter.
"""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from memu.memory_fs.exporter import slugify
from memu.prompts.memory_fs import (
    DESCRIPTIONS_PLACEHOLDER,
    MEMORY_SYNTHESIS_PROMPT,
    SKILL_SYNTHESIS_PROMPT,
)

if TYPE_CHECKING:
    from memu.memory_fs.exporter import FileDescription

ChatFn = Callable[[str], Awaitable[str]]


@dataclass
class SynthesisResult:
    """Synthesized artifact payloads, ready to hand to the exporter."""

    memory_body: str = ""
    skills: dict[str, str] = field(default_factory=dict)


class MemorySynthesizer:
    """Synthesize MEMORY/SKILL content from multimodal descriptions via an LLM."""

    def __init__(
        self,
        *,
        memory_prompt: str = MEMORY_SYNTHESIS_PROMPT,
        skill_prompt: str = SKILL_SYNTHESIS_PROMPT,
    ) -> None:
        self._memory_prompt = memory_prompt
        self._skill_prompt = skill_prompt

    async def synthesize(self, descriptions: list[FileDescription], *, chat: ChatFn) -> SynthesisResult:
        formatted = self._format(descriptions)
        if not formatted:
            return SynthesisResult()

        memory_raw = await chat(self._memory_prompt.replace(DESCRIPTIONS_PLACEHOLDER, formatted))
        skills_raw = await chat(self._skill_prompt.replace(DESCRIPTIONS_PLACEHOLDER, formatted))

        return SynthesisResult(
            memory_body=self._clean_markdown(memory_raw),
            skills=self._parse_skills(skills_raw),
        )

    @staticmethod
    def _format(descriptions: list[FileDescription]) -> str:
        lines = [
            f"- [{desc.modality}] {desc.url}: {desc.description}"
            for desc in descriptions
            if desc.description.strip()
        ]
        return "\n".join(lines)

    @staticmethod
    def _clean_markdown(raw: str) -> str:
        text = (raw or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\n", "", text)
            text = re.sub(r"\n```$", "", text).strip()
        return text

    def _parse_skills(self, raw: str) -> dict[str, str]:
        payload = self._extract_json_array(raw)
        if payload is None:
            return {}
        try:
            parsed = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            return {}
        if not isinstance(parsed, list):
            return {}

        skills: dict[str, str] = {}
        used: dict[str, int] = {}
        for entry in parsed:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            body = entry.get("body")
            if not isinstance(name, str) or not isinstance(body, str):
                continue
            body = body.strip()
            if not body:
                continue
            base = slugify(name)
            count = used.get(base, 0)
            slug = base if count == 0 else f"{base}-{count + 1}"
            used[base] = count + 1
            skills[slug] = body
        return skills

    @staticmethod
    def _extract_json_array(raw: str) -> str | None:
        if not raw:
            return None
        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return None
        return raw[start : end + 1]


__all__ = ["ChatFn", "MemorySynthesizer", "SynthesisResult"]
