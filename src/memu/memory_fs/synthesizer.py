"""LLM synthesis of the MEMORY/SKILL overview documents.

This is the optional, opt-in counterpart to the deterministic exporter. It synthesizes
the two root overview documents — ``MEMORY.md`` and ``SKILL.md`` — that sit above the
per-file payloads:

- ``MEMORY.md`` is synthesized from the per-source multimodal descriptions (the source
  trunk), merged into the prior overview.
- ``SKILL.md`` is synthesized from the bodies of the skill-track ``RecallFile``s (the
  skill trunk), merged into the prior overview.

The per-file payloads themselves (``memory/<slug>.md``, ``skill/<slug>.md``) and
``INDEX.md`` stay deterministic and are handled by the exporter. Skills are generated
and persisted inside the memorize workflow (ADR 0006); this layer only summarizes them.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from memu.prompts.memory_fs import (
    DESCRIPTIONS_PLACEHOLDER,
    EXISTING_PLACEHOLDER,
    MEMORY_SYNTHESIS_PROMPT,
    SKILL_OVERVIEW_SYNTHESIS_PROMPT,
)

if TYPE_CHECKING:
    from memu.database.models import RecallFile
    from memu.memory_fs.exporter import FileDescription

ChatFn = Callable[[str], Awaitable[str]]


class MemorySynthesizer:
    """Synthesize the MEMORY/SKILL overview documents via an LLM."""

    def __init__(
        self,
        *,
        memory_prompt: str = MEMORY_SYNTHESIS_PROMPT,
        skill_prompt: str = SKILL_OVERVIEW_SYNTHESIS_PROMPT,
    ) -> None:
        self._memory_prompt = memory_prompt
        self._skill_prompt = skill_prompt

    async def synthesize_memory(
        self,
        descriptions: list[FileDescription],
        *,
        existing_memory: str = "",
        chat: ChatFn,
    ) -> str:
        """Synthesize the ``MEMORY.md`` body from the per-source descriptions.

        Empty ``existing_memory`` builds from scratch; a populated value is merged into.
        Returns the prior body unchanged when there is nothing to synthesize.
        """
        formatted = self._format_descriptions(descriptions)
        if not formatted:
            return existing_memory
        prompt = self._memory_prompt.replace(EXISTING_PLACEHOLDER, existing_memory.strip() or "(empty)").replace(
            DESCRIPTIONS_PLACEHOLDER, formatted
        )
        return self._clean_markdown(await chat(prompt))

    async def synthesize_skill_overview(
        self,
        skills: list[RecallFile],
        *,
        existing_skill: str = "",
        chat: ChatFn,
    ) -> str:
        """Synthesize the ``SKILL.md`` overview from the skill-track files' bodies.

        The skill files are the full accumulated library (the memorize workflow merges
        per source), so the overview is regenerated from the whole set each time, merged
        into any prior overview. Returns the prior overview unchanged when empty.
        """
        formatted = self._format_skills(skills)
        if not formatted:
            return existing_skill
        prompt = self._skill_prompt.replace(EXISTING_PLACEHOLDER, existing_skill.strip() or "(empty)").replace(
            DESCRIPTIONS_PLACEHOLDER, formatted
        )
        return self._clean_markdown(await chat(prompt))

    @staticmethod
    def _format_descriptions(descriptions: list[FileDescription]) -> str:
        lines = [
            f"- [{desc.modality}] {desc.url}: {desc.description}" for desc in descriptions if desc.description.strip()
        ]
        return "\n".join(lines)

    @staticmethod
    def _format_skills(skills: list[RecallFile]) -> str:
        blocks = [
            f"## {skill.name}\n{(skill.content or '').strip()}".strip()
            for skill in sorted(skills, key=lambda s: s.name)
            if (skill.content or "").strip()
        ]
        return "\n\n".join(blocks)

    @staticmethod
    def _clean_markdown(raw: str) -> str:
        text = (raw or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\n", "", text)
            text = re.sub(r"\n```$", "", text).strip()
        return text


__all__ = ["ChatFn", "MemorySynthesizer"]
