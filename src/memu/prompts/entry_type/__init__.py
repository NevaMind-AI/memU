from memu.prompts.entry_type import description, event, knowledge, log, profile, tool

# Per-lane default entry types. Each lane runs the same extraction code path; only
# the entry-type set, prompts, and grouping cardinality differ (see ADR 0006).
LANE_ENTRY_TYPES: dict[str, list[str]] = {
    "index": ["description"],
    "memory": ["profile", "event"],
    "skill": ["tool", "log"],
}

# Backward-friendly alias: the historical flat default refers to the memory lane.
DEFAULT_ENTRY_TYPES: list[str] = list(LANE_ENTRY_TYPES["memory"])

PROMPTS: dict[str, str] = {
    "profile": profile.PROMPT.strip(),
    "event": event.PROMPT.strip(),
    "knowledge": knowledge.PROMPT.strip(),
    "tool": tool.PROMPT.strip(),
    "log": log.PROMPT.strip(),
    "description": description.PROMPT.strip(),
}

CUSTOM_PROMPTS: dict[str, dict[str, str]] = {
    "profile": profile.CUSTOM_PROMPT,
    "event": event.CUSTOM_PROMPT,
    "knowledge": knowledge.CUSTOM_PROMPT,
    "tool": tool.CUSTOM_PROMPT,
    "log": log.CUSTOM_PROMPT,
    "description": description.CUSTOM_PROMPT,
}

CUSTOM_TYPE_CUSTOM_PROMPTS: dict[str, str] = {
    "category": profile.CUSTOM_PROMPT["category"],
    "output": profile.CUSTOM_PROMPT["output"],
    "input": profile.CUSTOM_PROMPT["input"],
}

DEFAULT_MEMORY_CUSTOM_PROMPT_ORDINAL: dict[str, int] = {
    "objective": 10,
    "workflow": 20,
    "rules": 30,
    "category": 40,
    "output": 50,
    "examples": 60,
    "input": 90,
}

__all__ = [
    "CUSTOM_PROMPTS",
    "CUSTOM_TYPE_CUSTOM_PROMPTS",
    "DEFAULT_ENTRY_TYPES",
    "DEFAULT_MEMORY_CUSTOM_PROMPT_ORDINAL",
    "LANE_ENTRY_TYPES",
    "PROMPTS",
]
