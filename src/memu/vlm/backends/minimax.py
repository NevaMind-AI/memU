from __future__ import annotations

from memu.vlm.backends.openai import OpenAIVLMBackend


class MiniMaxVLMBackend(OpenAIVLMBackend):
    """Backend for MiniMax vision (OpenAI-compatible chat completions v2)."""

    name = "minimax"
    vision_endpoint = "/text/chatcompletion_v2"
