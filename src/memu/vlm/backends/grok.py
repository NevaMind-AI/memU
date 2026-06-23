from __future__ import annotations

from memu.vlm.backends.openai import OpenAIVLMBackend


class GrokVLMBackend(OpenAIVLMBackend):
    """Backend for Grok (xAI) vision (OpenAI-compatible)."""

    name = "grok"
