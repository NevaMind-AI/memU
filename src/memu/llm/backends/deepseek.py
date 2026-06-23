from __future__ import annotations

from memu.llm.backends.openai import OpenAILLMBackend


class DeepSeekLLMBackend(OpenAILLMBackend):
    """Backend for DeepSeek LLM API (OpenAI-compatible).

    Default base_url: ``https://api.deepseek.com/v1`` with model ``deepseek-v4-flash``.
    Inherits OpenAI's payload/response handling.
    """

    name = "deepseek"
    summary_endpoint = "/chat/completions"
