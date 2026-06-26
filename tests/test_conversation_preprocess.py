"""Tests for conversation preprocessing after segmentation was removed.

The conversation preprocessor now normalizes the chat log into an indexed,
line-based transcript and returns it as a single resource. It must not segment
the conversation nor call the LLM.
"""

from __future__ import annotations

import asyncio
from typing import Any

from memu.preprocess import preprocess_resource
from memu.preprocess.base import PreprocessContext


class _RecordingChatClient:
    """LLM client that records calls so the test can assert it is never used."""

    def __init__(self) -> None:
        self.calls = 0

    async def chat(self, *_: Any, **__: Any) -> str:
        self.calls += 1
        return ""


def _make_ctx(client: Any) -> PreprocessContext:
    return PreprocessContext(
        get_llm_client=lambda: client,
        get_vlm_client=lambda: None,
        escape_prompt_value=lambda s: s,
        extract_json_blob=lambda s: s,
        resolve_custom_prompt=lambda _p, _v: "",
        multimodal_preprocess_prompts={},
    )


def test_conversation_returns_single_unsegmented_resource() -> None:
    client = _RecordingChatClient()
    ctx = _make_ctx(client)
    raw = '[{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello"}]'

    result = asyncio.run(
        preprocess_resource(
            modality="conversation",
            local_path="/workspace/conv.json",
            text=raw,
            ctx=ctx,
            llm_client=client,
        )
    )

    # Whole conversation in a single segment, no caption, no LLM involvement.
    assert client.calls == 0
    assert len(result) == 1
    assert result[0]["caption"] is None
    text = result[0]["text"] or ""
    assert "[0] [user]: Hi" in text
    assert "[1] [assistant]: Hello" in text
