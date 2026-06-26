"""Conversation (chat) preprocessing.

Normalizes a chat log into an indexed, line-based transcript and returns it as a
single resource. The conversation is intentionally kept whole (no segmentation):
downstream memory extraction sees the complete, original transcript instead of an
LLM-rewritten or split version.
"""

from __future__ import annotations

from typing import Any

from memu.preprocess.base import (
    PreprocessContext,
    Preprocessor,
    PreprocessResult,
)
from memu.utils.conversation import format_conversation_for_preprocess


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
        # Use the original JSON-derived, indexed conversation text as-is. We do not
        # segment or summarize: keeping the whole transcript avoids dropping fields
        # (e.g. created_at) that an LLM rewrite/segmentation pass might lose.
        # ``template``/``llm_client`` are unused here but kept to satisfy the
        # ``Preprocessor.run`` contract (and template must stay non-empty so this
        # modality is dispatched through the text-normalization path).
        conversation_text = format_conversation_for_preprocess(text)
        return [{"text": conversation_text, "caption": None}]
