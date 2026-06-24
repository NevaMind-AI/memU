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

SKILL_SYNTHESIS_PROMPT = """You are maintaining an AI agent's skill library.

Below are the EXISTING skills (name + body), followed by NEW source descriptions
that were just added. From the descriptions, identify concrete, repeatable skills or
tool usage patterns (what worked, how to repeat it, what to avoid). Ignore one-off
facts, preferences, or trivia — those belong in the memory document, not here.

Return ONLY a JSON array of skills to add or replace. Each element is an object:
  {"name": "kebab-case-skill-name", "body": "Markdown body for this skill"}
- To revise an existing skill, reuse its exact name and return the full new body.
- To add a new skill, use a new name.
- Only include skills actually affected by the new descriptions; untouched existing
  skills are kept automatically.
- If there are no genuine skills to add or change, return an empty array: []

EXISTING skills:
__EXISTING__

NEW source descriptions:
__DESCRIPTIONS__
"""

__all__ = [
    "DESCRIPTIONS_PLACEHOLDER",
    "EXISTING_PLACEHOLDER",
    "MEMORY_SYNTHESIS_PROMPT",
    "SKILL_SYNTHESIS_PROMPT",
]
