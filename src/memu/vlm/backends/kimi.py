from __future__ import annotations

from memu.vlm.backends.openai import OpenAIVLMBackend


class KimiVLMBackend(OpenAIVLMBackend):
    """Backend for Kimi / Moonshot vision (OpenAI-compatible)."""

    name = "kimi"
