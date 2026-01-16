from __future__ import annotations

from memu.llm.backends.openai import OpenAILLMBackend


class GrokBackend(OpenAILLMBackend):
    """Backend for Grok (xAI) LLM API."""

    name = "grok"
    # Grok uses the same payload structure as OpenAI
    # We inherits build_summary_payload, parse_summary_response, etc.
