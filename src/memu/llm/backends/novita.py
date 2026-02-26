from __future__ import annotations

from memu.llm.backends.openai import OpenAILLMBackend


class NovitaBackend(OpenAILLMBackend):
    """Backend for Novita LLM API."""

    name = "novita"
    # Novita uses the same payload structure as OpenAI
