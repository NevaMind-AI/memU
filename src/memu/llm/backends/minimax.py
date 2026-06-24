from __future__ import annotations

from memu.llm.backends.openai import OpenAILLMBackend


class MiniMaxLLMBackend(OpenAILLMBackend):
    """Backend for MiniMax LLM API (OpenAI-compatible chat completions v2).

    Default base_url: ``https://api.minimax.io/v1`` with model ``MiniMax-M3``.
    MiniMax exposes an OpenAI-compatible chat endpoint at ``/text/chatcompletion_v2``.
    """

    name = "minimax"
    summary_endpoint = "/text/chatcompletion_v2"
