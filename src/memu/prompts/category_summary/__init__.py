from __future__ import annotations

from memu.prompts.category_summary.category import CUSTOM_PROMPT, PROMPT
from memu.prompts.category_summary.category_with_refs import CUSTOM_PROMPT as CUSTOM_PROMPT_WITH_REFS
from memu.prompts.category_summary.category_with_refs import PROMPT as PROMPT_WITH_REFS

DEFAULT_CATEGORY_SUMMARY_PROMPT_ORDINAL: dict[str, int] = {
    "objective": 10,
    "workflow": 20,
    "rules": 30,
    "output": 40,
    "examples": 50,
    "input": 90,
}

__all__ = [
    "CUSTOM_PROMPT",
    "CUSTOM_PROMPT_WITH_REFS",
    "DEFAULT_CATEGORY_SUMMARY_PROMPT_ORDINAL",
    "PROMPT",
    "PROMPT_WITH_REFS",
]
