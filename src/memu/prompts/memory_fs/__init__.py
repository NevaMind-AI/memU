"""Prompts for the optional memory_fs synthesis bypass.

Both prompts consume the shared trunk — the per-source multimodal descriptions —
and synthesize one of the sibling artifacts. The literal token ``__DESCRIPTIONS__``
is replaced (not ``str.format``) so description text containing braces is safe.
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

SKILL_UPDATE_PROMPT = """You are maintaining an AI agent's skill library.

Below are the EXISTING skills (name + body), followed by NEW source descriptions
that were just added.

Return ONLY a JSON array of skills to add or replace based on the new
descriptions. Each element is an object:
  {"name": "kebab-case-skill-name", "body": "Markdown body for this skill"}
- To revise an existing skill, reuse its exact name and return the full new body.
- To add a new skill, use a new name.
- Only include skills actually affected by the new descriptions.
- If the new descriptions contain nothing skill-worthy, return an empty array: []

EXISTING skills:
__EXISTING__

NEW source descriptions:
__DESCRIPTIONS__
"""

__all__ = [
    "DESCRIPTIONS_PLACEHOLDER",
    "EXISTING_PLACEHOLDER",
    "MEMORY_SYNTHESIS_PROMPT",
    "MEMORY_UPDATE_PROMPT",
    "SKILL_SYNTHESIS_PROMPT",
    "SKILL_UPDATE_PROMPT",
]
