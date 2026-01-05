from memu.prompts.memory_type import behavior, event, knowledge, profile, skill

# DEFAULT_MEMORY_TYPES: list[str] = ["profile", "event", "knowledge", "behavior"]
DEFAULT_MEMORY_TYPES: list[str] = ["profile", "event"]

PROMPTS: dict[str, str] = {
    "profile": profile.PROMPT.strip(),
    "event": event.PROMPT.strip(),
    "knowledge": knowledge.PROMPT.strip(),
    "behavior": behavior.PROMPT.strip(),
    "skill": skill.PROMPT.strip(),
}

CUSTOM_PROMPTS: dict[str, dict[str, str]] = {
    "profile": profile.CUSTOM_PROMPT,
    "event": event.CUSTOM_PROMPT,
    "knowledge": knowledge.CUSTOM_PROMPT,
    "behavior": behavior.CUSTOM_PROMPT,
    "skill": skill.CUSTOM_PROMPT,
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

__all__ = ["CUSTOM_PROMPTS", "DEFAULT_MEMORY_CUSTOM_PROMPT_ORDINAL", "DEFAULT_MEMORY_TYPES", "PROMPTS"]
