"""LLM synthesis of the MEMORY.md document from the shared description trunk.

This is the optional, opt-in counterpart to the deterministic exporter: instead of
rendering already-extracted category summaries, it feeds the per-source multimodal
descriptions to an LLM and synthesizes the memory document directly. ``INDEX.md``,
the ``skill/`` tree, and the root ``SKILL.md`` index stay deterministic and are
handled by the exporter (the ``skill/`` tree is built from the ``skill``-type
memory items extracted during memorize, not synthesized here).
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from memu.prompts.memory_fs import (
    DESCRIPTIONS_PLACEHOLDER,
    EXISTING_PLACEHOLDER,
    MEMORY_SYNTHESIS_PROMPT,
    MEMORY_UPDATE_PROMPT,
)

if TYPE_CHECKING:
    from memu.memory_fs.exporter import FileDescription

ChatFn = Callable[[str], Awaitable[str]]


class MemorySynthesizer:
    """Synthesize the ``MEMORY.md`` body from multimodal descriptions via an LLM."""

    def __init__(
        self,
        *,
        memory_prompt: str = MEMORY_SYNTHESIS_PROMPT,
        memory_update_prompt: str = MEMORY_UPDATE_PROMPT,
    ) -> None:
        self._memory_prompt = memory_prompt
        self._memory_update_prompt = memory_update_prompt

    async def synthesize(self, descriptions: list[FileDescription], *, chat: ChatFn) -> str:
        """Initialization: build the MEMORY.md body from scratch over all descriptions."""
        formatted = self._format(descriptions)
        if not formatted:
            return ""
        memory_raw = await chat(self._memory_prompt.replace(DESCRIPTIONS_PLACEHOLDER, formatted))
        return self._clean_markdown(memory_raw)

    async def update(
        self,
        descriptions: list[FileDescription],
        *,
        existing_memory: str,
        chat: ChatFn,
    ) -> str:
        """Incremental: merge the changed descriptions into the existing MEMORY.md body."""
        formatted = self._format(descriptions)
        if not formatted:
            return existing_memory
        memory_prompt = self._memory_update_prompt.replace(
            EXISTING_PLACEHOLDER, existing_memory.strip() or "(empty)"
        ).replace(DESCRIPTIONS_PLACEHOLDER, formatted)
        memory_raw = await chat(memory_prompt)
        return self._clean_markdown(memory_raw)

    @staticmethod
    def _format(descriptions: list[FileDescription]) -> str:
        lines = [
            f"- [{desc.modality}] {desc.url}: {desc.description}" for desc in descriptions if desc.description.strip()
        ]
        return "\n".join(lines)

    @staticmethod
    def _clean_markdown(raw: str) -> str:
        text = (raw or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\n", "", text)
            text = re.sub(r"\n```$", "", text).strip()
        return text


__all__ = ["ChatFn", "MemorySynthesizer"]
