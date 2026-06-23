"""Image preprocessing.

Extracts a detailed description and caption from an image using the Vision API.
"""

from __future__ import annotations

from typing import Any

from memu.preprocess.base import (
    PreprocessContext,
    Preprocessor,
    PreprocessResult,
    parse_multimodal_response,
)


class ImagePreprocessor(Preprocessor):
    modality = "image"
    requires_text = False

    async def run(
        self,
        *,
        local_path: str,
        text: str | None,
        template: str,
        ctx: PreprocessContext,
        llm_client: Any | None = None,
    ) -> PreprocessResult:
        client = llm_client or ctx.get_vlm_client()
        processed = await client.vision(prompt=template, image_path=local_path, system_prompt=None)
        description, caption = parse_multimodal_response(processed, "detailed_description", "caption")
        return [{"text": description, "caption": caption}]
