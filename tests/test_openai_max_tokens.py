"""Regression tests for OpenAI token-limit parameter handling.

Newer OpenAI models (GPT-5 family, the shipped defaults) reject ``max_tokens``
and ``max_tokens=None`` outright, requiring ``max_completion_tokens`` instead.
The SDK clients must therefore omit the parameter when unset and use
``max_completion_tokens`` when a value is provided.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from openai import omit

from memu.llm.openai_client import OpenAIClient
from memu.vlm.openai_client import OpenAIVLMClient


class _RecordingCompletions:
    def __init__(self) -> None:
        self.kwargs: dict[str, Any] = {}

    async def create(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))])


class _RecordingOpenAI:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=_RecordingCompletions())


def test_llm_chat_omits_max_tokens_when_unset() -> None:
    client = OpenAIClient(base_url="https://example.test", api_key="k", chat_model="gpt-5.4-mini")
    fake = _RecordingOpenAI()
    client.client = fake  # type: ignore[assignment]

    asyncio.run(client.chat("hi"))

    kwargs = fake.chat.completions.kwargs
    # ``max_tokens`` is never sent; the token limit is omitted via the SDK
    # ``omit`` sentinel (the SDK drops it from the request body).
    assert "max_tokens" not in kwargs
    assert kwargs.get("max_completion_tokens") is omit


def test_llm_chat_uses_max_completion_tokens_when_set() -> None:
    client = OpenAIClient(base_url="https://example.test", api_key="k", chat_model="gpt-5.4-mini")
    fake = _RecordingOpenAI()
    client.client = fake  # type: ignore[assignment]

    asyncio.run(client.chat("hi", max_tokens=64))

    kwargs = fake.chat.completions.kwargs
    assert kwargs.get("max_completion_tokens") == 64
    assert "max_tokens" not in kwargs


def test_vlm_vision_token_param(tmp_path: Path) -> None:
    image = tmp_path / "x.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n")

    client = OpenAIVLMClient(base_url="https://example.test", api_key="k", vlm_model="gpt-5.4")
    fake = _RecordingOpenAI()
    client.client = fake  # type: ignore[assignment]

    asyncio.run(client.vision("describe", str(image)))
    assert "max_tokens" not in fake.chat.completions.kwargs
    assert fake.chat.completions.kwargs.get("max_completion_tokens") is omit

    asyncio.run(client.vision("describe", str(image), max_tokens=128))
    assert fake.chat.completions.kwargs.get("max_completion_tokens") == 128
    assert "max_tokens" not in fake.chat.completions.kwargs
