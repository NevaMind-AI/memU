"""Prompts for the optional memory_fs synthesis bypass.

Both prompts consume the shared trunk — the per-source multimodal descriptions —
plus the current state of the artifact they maintain, and emit the updated artifact.
There is a single prompt per artifact: a from-scratch build is just the same prompt
with an empty ``__EXISTING__`` block. The literal tokens ``__DESCRIPTIONS__`` and
``__EXISTING__`` are replaced (not ``str.format``) so text containing braces is safe.
"""

from __future__ import annotations

DESCRIPTIONS_PLACEHOLDER = "__DESCRIPTIONS__"
EXISTING_PLACEHOLDER = "__EXISTING__"

MEMORY_SYNTHESIS_PROMPT = """You are maintaining an AI agent's long-term memory document about a user.

Below is the CURRENT memory document, followed by NEW source descriptions — one per
source file the agent has seen. Produce the updated memory document.

Requirements:
- Merge new facts, revise statements the new descriptions make outdated, and keep
  existing content that is still valid. If the CURRENT document is empty, synthesize
  a fresh document from the descriptions alone.
- Output the FULL Markdown document only. Do not wrap it in code fences.
- Use second-level headings (##) for sections such as Profile, Preferences, Goals,
  and Key Events. Include a section only if there is real content for it.
- Be concise and factual. Do not invent details that are not supported by the
  descriptions. Write in the same language as the descriptions.

CURRENT memory document:
__EXISTING__

NEW source descriptions:
__DESCRIPTIONS__
"""

__all__ = [
    "DESCRIPTIONS_PLACEHOLDER",
    "EXISTING_PLACEHOLDER",
    "MEMORY_SYNTHESIS_PROMPT",
]
