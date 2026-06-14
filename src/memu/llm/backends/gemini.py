from __future__ import annotations

from memu.llm.backends.openai import OpenAILLMBackend


class GeminiLLMBackend(OpenAILLMBackend):
    """Backend for Google Gemini via its OpenAI-compatible API endpoint."""

    name = "gemini"
    # Gemini's OpenAI-compatible chat endpoint is the same as OpenAI's
    summary_endpoint = "/chat/completions"
