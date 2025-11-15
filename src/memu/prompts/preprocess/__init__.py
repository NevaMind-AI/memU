from memu.prompts.preprocess import conversation

PROMPTS: dict[str, str] = {
    "conversation": conversation.PROMPT.strip(),
}

__all__ = ["PROMPTS"]
