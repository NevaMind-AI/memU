from __future__ import annotations

from memu.vlm.backends.openai import OpenAIVLMBackend


class OpenRouterVLMBackend(OpenAIVLMBackend):
    """Backend for OpenRouter vision (OpenAI-compatible)."""

    name = "openrouter"
    vision_endpoint = "/api/v1/chat/completions"
