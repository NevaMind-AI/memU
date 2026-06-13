from __future__ import annotations

from memu.llm.backends.openai import OpenAILLMBackend


class LiteLLMBackend(OpenAILLMBackend):
    """Backend for LiteLLM AI gateway proxy (OpenAI-compatible)."""

    name = "litellm"
