from __future__ import annotations

from typing import ClassVar

from memu.vlm.backends.openai import OpenAIVLMBackend


class OpenRouterVLMBackend(OpenAIVLMBackend):
    """Backend for OpenRouter vision + native video (OpenAI-compatible).

    OpenRouter accepts whole videos via the ``video_url`` content type (a direct
    URL or a base64 ``data:`` URL) on its chat-completions endpoint, routing them
    to video-capable models (e.g. ``minimax/minimax-m3``, ``z-ai/glm-4.6v``).
    """

    name = "openrouter"
    vision_endpoint = "/api/v1/chat/completions"
    video_endpoint = "/api/v1/chat/completions"
    supports_video: ClassVar[bool] = True
