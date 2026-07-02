"""Prompts for the resource -> file memorize path (ADR 0007 phase 1) and the
legacy memory_fs synthesis bypass.

Two families live here:

- The single-shot synthesis prompts (``*_SYNTHESIS_PROMPT``) — the legacy bypass
  that consumes the shared trunk plus the current artifact and emits it wholesale.
- The two-step resource -> file prompts (``ROUTE_PROMPTS`` / ``SYNTHESIS_PROMPTS``),
  keyed by track (``"memory"`` / ``"skill"``): step (a) routes a source to the set of
  files to update/create; step (b) writes each target file's body. Both are track
  parametric so the workspace workflow drives chat and skill through one code path.

The literal placeholder tokens (``__DESCRIPTIONS__``, ``__EXISTING__``, ``__CONTENT__``,
``__NAME__``, ``__DESCRIPTION__``) are replaced (not ``str.format``) so source text
containing braces is safe.
"""

from __future__ import annotations

DESCRIPTIONS_PLACEHOLDER = "__DESCRIPTIONS__"
EXISTING_PLACEHOLDER = "__EXISTING__"
CONTENT_PLACEHOLDER = "__CONTENT__"
NAME_PLACEHOLDER = "__NAME__"
DESCRIPTION_PLACEHOLDER = "__DESCRIPTION__"

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

SKILL_OVERVIEW_SYNTHESIS_PROMPT = """You are maintaining the overview page of an AI agent's skill library.

Below is the CURRENT overview, followed by the full set of SKILLS currently in the
library (name + body). Produce the updated overview document.

Requirements:
- Write a concise overview of what the agent knows how to do: group related skills,
  call out the most important ones, and orient a reader to the library. Do not paste
  each skill's full body — the bodies live in their own files.
- Output the FULL Markdown document only. Do not wrap it in code fences.
- Use second-level headings (##) for groupings when there are enough skills to warrant
  them. If there are no skills, output a short note that the library is empty.
- Be concise and factual. Write in the same language as the skills.

CURRENT overview:
__EXISTING__

SKILLS in the library:
__DESCRIPTIONS__
"""

SKILL_FILE_SYNTHESIS_PROMPT = """You are maintaining an AI agent's skill library.

Below are the EXISTING skills (name + body), followed by the CONTENT of a single source
the agent just processed. From the content, identify concrete, repeatable skills or tool
usage patterns (what worked, how to repeat it, what to avoid). Ignore one-off facts,
preferences, or trivia — those belong in the memory document, not here.

Return ONLY a JSON array of skills to add or replace. Each element is an object:
  {"name": "kebab-case-skill-name", "description": "one-line summary of the skill", "body": "Markdown body for this skill"}
- To revise an existing skill, reuse its exact name and return the full new body.
- To add a new skill, use a new name.
- Only include skills actually affected by this content; untouched existing skills are
  kept automatically.
- If there are no genuine skills to add or change, return an empty array: []

EXISTING skills:
__EXISTING__

NEW source content:
__DESCRIPTIONS__
"""

# --- Two-step resource -> file prompts (ADR 0007 phase 1) ---------------------
#
# Step (a): route a single source to the set of files to update/create. The model
# sees the existing files (name + one-line description) and the source content, and
# returns a JSON plan. Step (b): given one target file (name + description + current
# body) and the source content, write the file's full body.

_MEMORY_ROUTE_PROMPT = """You are maintaining an AI agent's long-term memory about a user, organized as a set
of memory files (each a themed document — e.g. Profile, Preferences, Goals, Work).

Below are the EXISTING memory files (name + one-line description), followed by the
CONTENT of a single source the agent just processed. Decide which files this source
should update, and whether any new file should be created for facts that fit no
existing file. Capture durable facts, preferences, goals, and notable events; ignore
throwaway chatter.

Return ONLY a JSON array of operations. Each element is an object:
  {"op": "update", "name": "<exact existing file name>"}
  {"op": "create", "name": "<concise Title Case file name>", "description": "one-line summary of the file"}
- Use "update" with a file's EXACT existing name to route the source there.
- Use "create" only when no existing file fits; give a reusable name and a description.
- Prefer updating an existing file over creating a near-duplicate.
- List a file at most once. If the source has nothing memory-worthy, return [].

EXISTING memory files:
__EXISTING__

SOURCE content:
__CONTENT__
"""

_SKILL_ROUTE_PROMPT = """You are maintaining an AI agent's skill library — a set of skill files, each a
concrete, repeatable how-to (what worked, how to repeat it, what to avoid).

Below are the EXISTING skills (name + one-line description), followed by the CONTENT of
a single source the agent just processed. Identify concrete, repeatable skills or tool
usage patterns in the content and decide which skills to update or create. Ignore
one-off facts, preferences, or trivia — those belong in memory, not here.

Return ONLY a JSON array of operations. Each element is an object:
  {"op": "update", "name": "<exact existing skill name>"}
  {"op": "create", "name": "kebab-case-skill-name", "description": "one-line summary of the skill"}
- Use "update" with a skill's EXACT existing name to revise it.
- Use "create" only when no existing skill fits; give a new kebab-case name and a description.
- Prefer updating an existing skill over creating a near-duplicate.
- List a skill at most once. If the source has no genuine skills, return [].

EXISTING skills:
__EXISTING__

SOURCE content:
__CONTENT__
"""

_MEMORY_FILE_SYNTHESIS_PROMPT = """You are maintaining a single memory file about a user.

FILE name: __NAME__
FILE description: __DESCRIPTION__

Below is the CURRENT content of this file (empty if it is being created), followed by the
CONTENT of a new source. Produce the updated file.

Requirements:
- Merge in facts from the source that belong in THIS file, revise statements the source
  makes outdated, and keep existing content that is still valid. If the CURRENT content
  is empty, synthesize a fresh document from the source alone.
- Only include material relevant to this file's topic; leave unrelated facts out.
- Output the FULL Markdown document only. Do not wrap it in code fences.
- Be concise and factual. Do not invent details not supported by the source. Write in the
  same language as the source.

CURRENT content:
__EXISTING__

NEW source content:
__CONTENT__
"""

_SKILL_FILE_SYNTHESIS_PROMPT = """You are maintaining a single skill file in an AI agent's skill library.

SKILL name: __NAME__
SKILL description: __DESCRIPTION__

Below is the CURRENT body of this skill (empty if it is being created), followed by the
CONTENT of a new source. Produce the updated skill body.

Requirements:
- Capture the concrete, repeatable procedure this skill describes: what it accomplishes,
  the steps to repeat it, and pitfalls to avoid. Merge in what the source adds and revise
  anything it supersedes. If the CURRENT body is empty, write it fresh from the source.
- Output the FULL Markdown body only. Do not wrap it in code fences.
- Be concise and actionable. Do not invent steps not supported by the source. Write in the
  same language as the source.

CURRENT body:
__EXISTING__

NEW source content:
__CONTENT__
"""

# Track-keyed dispatch tables used by the workspace memorize workflow.
ROUTE_PROMPTS: dict[str, str] = {
    "memory": _MEMORY_ROUTE_PROMPT,
    "skill": _SKILL_ROUTE_PROMPT,
}
SYNTHESIS_PROMPTS: dict[str, str] = {
    "memory": _MEMORY_FILE_SYNTHESIS_PROMPT,
    "skill": _SKILL_FILE_SYNTHESIS_PROMPT,
}

__all__ = [
    "CONTENT_PLACEHOLDER",
    "DESCRIPTIONS_PLACEHOLDER",
    "DESCRIPTION_PLACEHOLDER",
    "EXISTING_PLACEHOLDER",
    "MEMORY_SYNTHESIS_PROMPT",
    "NAME_PLACEHOLDER",
    "ROUTE_PROMPTS",
    "SKILL_FILE_SYNTHESIS_PROMPT",
    "SKILL_OVERVIEW_SYNTHESIS_PROMPT",
    "SYNTHESIS_PROMPTS",
]
