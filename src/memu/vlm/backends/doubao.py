from __future__ import annotations

from memu.vlm.backends.openai import OpenAIVLMBackend


class DoubaoVLMBackend(OpenAIVLMBackend):
    """Backend for Doubao vision (OpenAI-compatible)."""

    name = "doubao"
    vision_endpoint = "/api/v3/chat/completions"
