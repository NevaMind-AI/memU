from __future__ import annotations

from memu.llm.backends.openai import OpenAILLMBackend


class KimiLLMBackend(OpenAILLMBackend):
    """Backend for Kimi / Moonshot LLM API (OpenAI-compatible).

    Default base_url: ``https://api.moonshot.cn/v1`` with model ``kimi-k2.7-code-highspeed``.
    Inherits OpenAI's payload/response handling.
    """

    name = "kimi"
    summary_endpoint = "/chat/completions"
