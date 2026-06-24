"""Video preprocessing.

Extracts the middle frame from a video and analyzes it with the Vision API to
produce a description and caption.
"""

from __future__ import annotations

import logging
import pathlib
from typing import Any

from memu.preprocess.base import (
    PreprocessContext,
    Preprocessor,
    PreprocessResult,
    parse_multimodal_response,
)
from memu.utils.video import VideoFrameExtractor

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
            if not VideoFrameExtractor.is_ffmpeg_available():
                logger.warning("ffmpeg not available, cannot process video. Returning None.")
                return [{"text": None, "caption": None}]

            logger.info(f"Extracting frame from video: {local_path}")
            frame_path = VideoFrameExtractor.extract_middle_frame(local_path)

            try:
                logger.info(f"Analyzing video frame with Vision API: {frame_path}")
                client = llm_client or ctx.get_vlm_client()
                processed = await client.vision(prompt=template, image_path=frame_path, system_prompt=None)
                description, caption = parse_multimodal_response(processed, "detailed_description", "caption")
                return [{"text": description, "caption": caption}]
            finally:
                try:
                    pathlib.Path(frame_path).unlink(missing_ok=True)
                    logger.debug(f"Cleaned up temporary frame: {frame_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up frame {frame_path}: {e}")

        except Exception as e:
            logger.error(f"Video preprocessing failed: {e}", exc_info=True)
            return [{"text": None, "caption": None}]
