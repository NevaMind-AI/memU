"""Conversation (chat) preprocessing.

Segments a conversation into topical chunks and produces a caption per segment.
"""

from __future__ import annotations

import logging
from typing import Any

from memu.preprocess.base import (
    PreprocessContext,
    Preprocessor,
    PreprocessResult,
    parse_conversation_segments,
)
from memu.utils.conversation import format_conversation_for_preprocess

logger = logging.getLogger(__name__)


class ConversationPreprocessor(Preprocessor):
    modality = "conversation"
    requires_text = True

    async def run(
        self,
        *,
        local_path: str,
        text: str | None,
        template: str,
        ctx: PreprocessContext,
        llm_client: Any | None = None,
    ) -> PreprocessResult:
        assert text is not None  # guaranteed by requires_text dispatch  # noqa: S101
        preprocessed_text = format_conversation_for_preprocess(text)
        prompt = template.format(conversation=ctx.escape_prompt_value(preprocessed_text))
        client = llm_client or ctx.get_llm_client()
        processed = await client.chat(prompt)
        _conv, segments = parse_conversation_segments(processed, ctx.extract_json_blob)

        # Important: always use the original JSON-derived, indexed conversation text for
        # downstream segmentation and memory extraction. The LLM may rewrite the
        # conversation and drop fields like created_at, which would cause them to be lost.
        conversation_text = preprocessed_text
        if not segments:
            return [{"text": conversation_text, "caption": None}]

        lines = conversation_text.split("\n")
        max_idx = len(lines) - 1
        resources: PreprocessResult = []

        for segment in segments:
            start = int(segment.get("start", 0))
            end = int(segment.get("end", max_idx))
            start = max(0, min(start, max_idx))
            end = max(0, min(end, max_idx))
            segment_text = "\n".join(lines[start : end + 1])

            if segment_text.strip():
                caption = await _summarize_segment(segment_text, client)
                resources.append({"text": segment_text, "caption": caption})
        return resources if resources else [{"text": conversation_text, "caption": None}]


async def _summarize_segment(segment_text: str, client: Any) -> str | None:
    """Summarize a single conversation segment in 1-2 sentences."""
    system_prompt = (
        "Summarize the given conversation segment in 1-2 concise sentences. Focus on the main topic or theme discussed."
    )
    try:
        response = await client.chat(segment_text, system_prompt=system_prompt)
        return response.strip() if response else None
    except Exception:
        logger.exception("Failed to summarize segment")
        return None
