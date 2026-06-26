"""Tests for audio preprocessing: type classification + overview + caption.

The audio preprocessor turns a transcription into cleaned content prefixed with
an "Audio Overview" (type/language/speakers/topic) and a one-sentence caption
that begins with the inferred audio type (song, conversation, lecture, ...).
"""

from __future__ import annotations

import asyncio
from typing import Any

from memu.preprocess import preprocess_resource
from memu.preprocess.base import PreprocessContext
from memu.prompts.preprocess import PROMPTS


class _RecordingChatClient:
    """Chat client that records the prompt and returns a tagged response."""

    def __init__(self, response: str) -> None:
        self.prompts: list[str] = []
        self._response = response

    async def chat(self, prompt: str, **_: Any) -> str:
        self.prompts.append(prompt)
        return self._response


def _make_ctx(client: Any) -> PreprocessContext:
    return PreprocessContext(
        get_llm_client=lambda: client,
        get_vlm_client=lambda: None,
        escape_prompt_value=lambda s: s,
        extract_json_blob=lambda s: s,
        resolve_custom_prompt=lambda _p, _v: "",
        multimodal_preprocess_prompts={},
    )


def test_audio_prompt_asks_to_classify_type() -> None:
    template = PROMPTS["audio"]
    assert "{transcription}" in template
    # The prompt should steer the model toward classifying the audio nature.
    for keyword in ("Classify the Audio", "conversation", "song", "Audio Overview", "Type:"):
        assert keyword in template


def test_audio_preprocess_returns_overview_and_typed_caption() -> None:
    response = (
        "<processed_content>## Audio Overview\n"
        "- Type: song\n"
        "- Language: English\n"
        "- Speakers: 1\n"
        "- Topic: love\n\n"
        "La la la, all you need is love.</processed_content>"
        "<caption>A song about love and togetherness.</caption>"
    )
    client = _RecordingChatClient(response)
    ctx = _make_ctx(client)

    # Text is already provided, so transcription is skipped and the chat prompt runs.
    result = asyncio.run(
        preprocess_resource(
            modality="audio",
            local_path="/workspace/track.mp3",
            text="la la la all you need is love",
            ctx=ctx,
            llm_client=client,
        )
    )

    # The transcription is injected into the classification prompt.
    assert "la la la all you need is love" in client.prompts[0]
    assert "## Audio Overview" in (result[0]["text"] or "")
    assert "Type: song" in (result[0]["text"] or "")
    assert result[0]["caption"] == "A song about love and togetherness."


def test_audio_preprocess_skips_without_text() -> None:
    # No text and a non-audio/non-text extension: nothing to transcribe.
    client = _RecordingChatClient("<processed_content>x</processed_content><caption>y</caption>")
    ctx = _make_ctx(client)

    result = asyncio.run(
        preprocess_resource(
            modality="audio",
            local_path="/workspace/mystery.bin",
            text=None,
            ctx=ctx,
            llm_client=client,
        )
    )

    assert result == [{"text": None, "caption": None}]
    assert client.prompts == []
