from memu.prompts.memory_type import behavior, event, knowledge, profile, skill

DEFAULT_MEMORY_TYPES: list[str] = ["profile", "event", "knowledge", "behavior"]

PROMPTS: dict[str, str] = {
    "profile": profile.PROMPT.strip(),
    "event": event.PROMPT.strip(),
    "knowledge": knowledge.PROMPT.strip(),
    "behavior": behavior.PROMPT.strip(),
    "skill": skill.PROMPT.strip(),
}

__all__ = ["DEFAULT_MEMORY_TYPES", "PROMPTS"]
