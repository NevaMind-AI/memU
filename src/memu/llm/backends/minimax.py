from __future__ import annotations

from memu.llm.backends.openai import OpenAILLMBackend


class MiniMaxLLMBackend(OpenAILLMBackend):
    """Backend for MiniMax LLM API (OpenAI-compatible).

    MiniMax provides OpenAI-compatible API endpoints.
    Supported models: MiniMax-M2.5, MiniMax-M2.5-highspeed.
    """

    name = "minimax"
    # MiniMax uses the same /chat/completions endpoint and payload structure as OpenAI.
    # We inherit build_summary_payload, parse_summary_response, build_vision_payload, etc.
