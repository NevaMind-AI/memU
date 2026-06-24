"""LLM synthesis of the MEMORY artifact from the shared description trunk.

This is the optional, opt-in counterpart to the deterministic exporter: instead of
rendering already-extracted database summaries, it feeds the per-source multimodal
descriptions to an LLM and synthesizes the memory document directly. ``INDEX.md``
stays deterministic and is handled by the exporter.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from memu.prompts.memory_fs import (
    DESCRIPTIONS_PLACEHOLDER,
    EXISTING_PLACEHOLDER,
    MEMORY_SYNTHESIS_PROMPT,
)

if TYPE_CHECKING:
    from memu.memory_fs.exporter import FileDescription

ChatFn = Callable[[str], Awaitable[str]]


class MemorySynthesizer:
    """Synthesize MEMORY content from multimodal descriptions via an LLM."""

    def __init__(self, *, memory_prompt: str = MEMORY_SYNTHESIS_PROMPT) -> None:
        self._memory_prompt = memory_prompt

    async def synthesize(
        self,
        descriptions: list[FileDescription],
        *,
        existing_memory: str = "",
        chat: ChatFn,
    ) -> str:
        """Synthesize MEMORY from the descriptions, merging into any existing body.

        Pass empty ``existing_memory`` (the default) to build from scratch; pass the
        prior body to incrementally fold the (changed) descriptions into it.
        """
        formatted = self._format(descriptions)
        if not formatted:
            return existing_memory
        prompt = self._memory_prompt.replace(EXISTING_PLACEHOLDER, existing_memory.strip() or "(empty)").replace(
            DESCRIPTIONS_PLACEHOLDER, formatted
        )
        return self._clean_markdown(await chat(prompt))

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
