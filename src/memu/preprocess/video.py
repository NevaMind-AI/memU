"""Video preprocessing.

The whole video file is analyzed natively in a single call (e.g. video-capable
models via OpenRouter's ``video_url`` content type) so its sampled frames and
temporal changes inform the description. Native video understanding is required:
when the configured VLM client does not support it, the video is skipped rather
than degraded to a single still frame.
"""

from __future__ import annotations

import logging
from typing import Any

from memu.preprocess.base import (
    PreprocessContext,
    Preprocessor,
    PreprocessResult,
    parse_multimodal_response,
)

logger = logging.getLogger(__name__)


class VideoPreprocessor(Preprocessor):
    modality = "video"
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
        try:
            client = llm_client or ctx.get_vlm_client()

            if not getattr(client, "supports_video", False):
                logger.error(
                    "Video preprocessing requires a VLM client with native video support "
                    "(supports_video=True), e.g. an OpenRouter video-capable model. "
                    "Middle-frame fallback is disabled; skipping video: %s",
                    local_path,
                )
                return [{"text": None, "caption": None}]

            return await self._run_native(local_path=local_path, template=template, client=client)
        except Exception as e:
            logger.error(f"Video preprocessing failed: {e}", exc_info=True)
            return [{"text": None, "caption": None}]

    async def _run_native(self, *, local_path: str, template: str, client: Any) -> PreprocessResult:
        """Analyze the whole video natively (frames + audio) in a single call."""
        logger.info(f"Analyzing video natively with VLM video API: {local_path}")
        processed = await client.video(prompt=template, video_path=local_path, system_prompt=None)
        description, caption = parse_multimodal_response(processed, "detailed_description", "caption")
        return [{"text": description, "caption": caption}]
