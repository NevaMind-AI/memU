"""Document (log / text) preprocessing.

Condenses document text and extracts a short caption.
"""

from __future__ import annotations

from typing import Any

from memu.preprocess.base import (
    PreprocessContext,
    Preprocessor,
    PreprocessResult,
    parse_multimodal_response,
)


class DocumentPreprocessor(Preprocessor):
    modality = "document"
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
        prompt = template.format(document_text=ctx.escape_prompt_value(text))
        client = llm_client or ctx.get_llm_client()
        processed = await client.chat(prompt)
        processed_content, caption = parse_multimodal_response(processed, "processed_content", "caption")
        return [{"text": processed_content or text, "caption": caption}]
