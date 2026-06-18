"""Prompts for the optional memory_fs synthesis bypass.

Both prompts consume the shared trunk — the per-source multimodal descriptions —
and synthesize one of the sibling artifacts. The literal token ``__DESCRIPTIONS__``
is replaced (not ``str.format``) so description text containing braces is safe.
"""

from __future__ import annotations

DESCRIPTIONS_PLACEHOLDER = "__DESCRIPTIONS__"

MEMORY_SYNTHESIS_PROMPT = """You are maintaining an AI agent's long-term memory about a user.

Below is a list of source descriptions — one per source file the agent has seen.
Synthesize them into a single, well-organized Markdown memory document.

Requirements:
- Output Markdown only. Do not wrap it in code fences.
- Use second-level headings (##) for sections such as Profile, Preferences,
  Goals, and Key Events. Include a section only if there is real content for it.
- Be concise and factual. Do not invent details that are not supported by the
  descriptions.
- Write in the same language as the descriptions.

Source descriptions:
__DESCRIPTIONS__
"""

SKILL_SYNTHESIS_PROMPT = """You are extracting reusable skills and tool patterns for an AI agent.

From the source descriptions below, identify concrete, repeatable skills or tool
usage patterns (what worked, how to repeat it, what to avoid). Ignore one-off
facts, preferences, or trivia — those belong in the memory document, not here.

Return ONLY a JSON array. Each element is an object:
  {"name": "kebab-case-skill-name", "body": "Markdown body for this skill"}
The "body" should be a self-contained Markdown skill document.
If there are no genuine skills, return an empty array: []

Source descriptions:
__DESCRIPTIONS__
"""

__all__ = [
    "DESCRIPTIONS_PLACEHOLDER",
    "MEMORY_SYNTHESIS_PROMPT",
    "SKILL_SYNTHESIS_PROMPT",
]
