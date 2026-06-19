"""Prompts for the optional MEMORY.md synthesis mode.

These prompts consume the shared trunk — the per-source multimodal descriptions —
and synthesize the ``MEMORY.md`` body. The literal token ``__DESCRIPTIONS__`` is
replaced (not ``str.format``) so description text containing braces is safe. The
``skill/`` tree is not synthesized here; it is built by the exporter from the
``skill``-type memory items extracted during memorize.
"""

from __future__ import annotations

DESCRIPTIONS_PLACEHOLDER = "__DESCRIPTIONS__"
EXISTING_PLACEHOLDER = "__EXISTING__"

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

MEMORY_UPDATE_PROMPT = """You are maintaining an AI agent's long-term memory document.

Below is the CURRENT memory document, followed by NEW source descriptions that
were just added. Update the document to incorporate the new information.

Requirements:
- Merge new facts, revise statements the new descriptions make outdated, and keep
  existing content that is still valid.
- Output the FULL updated Markdown document only. Do not wrap it in code fences.
- Keep the same heading structure (## Profile, ## Preferences, ## Goals, ## Key
  Events, ...). Add or drop sections as the content warrants.
- Be concise and factual; do not invent unsupported details. Use the same language
  as the descriptions.

CURRENT memory document:
__EXISTING__

NEW source descriptions:
__DESCRIPTIONS__
"""

__all__ = [
    "DESCRIPTIONS_PLACEHOLDER",
    "EXISTING_PLACEHOLDER",
    "MEMORY_SYNTHESIS_PROMPT",
    "MEMORY_UPDATE_PROMPT",
]
