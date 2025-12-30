from __future__ import annotations

from memu.prompts.category_summary.category import CUSTOM_PROMPT, PROMPT

DEFAULT_CATEGORY_SUMMARY_PROMPT_ORDINAL: dict[str, int] = {
    "objective": 10,
    "workflow": 20,
    "output": 30,
    "examples": 40,
    "input": 90,
}

__all__ = ["CUSTOM_PROMPT", "DEFAULT_CATEGORY_SUMMARY_PROMPT_ORDINAL", "PROMPT"]
