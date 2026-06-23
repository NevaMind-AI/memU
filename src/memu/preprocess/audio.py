"""Audio preprocessing.

Audio is first turned into text (via transcription or a sidecar text file) by
``prepare_audio_text`` in :mod:`memu.preprocess`, then formatted and captioned here.
"""

from __future__ import annotations

import logging
import pathlib
from typing import Any, cast

from memu.preprocess.base import (
    PreprocessContext,
    Preprocessor,
    PreprocessResult,
    parse_multimodal_response,
)

logger = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"}
TEXT_EXTENSIONS = {".txt", ".text"}


class AudioPreprocessor(Preprocessor):
    modality = "audio"
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
        assert text is not None  # transcription resolved before dispatch  # noqa: S101
        prompt = template.format(transcription=ctx.escape_prompt_value(text))
        client = llm_client or ctx.get_llm_client()
        processed = await client.chat(prompt)
        processed_content, caption = parse_multimodal_response(processed, "processed_content", "caption")
        return [{"text": processed_content or text, "caption": caption}]


async def prepare_audio_text(
    local_path: str,
    text: str | None,
    ctx: PreprocessContext,
    llm_client: Any | None = None,
) -> str | None:
    """Ensure audio resources provide text via transcription or file read."""
    if text:
        return text

    file_ext = pathlib.Path(local_path).suffix.lower()

    if file_ext in AUDIO_EXTENSIONS:
        try:
            logger.info(f"Transcribing audio file: {local_path}")
            client = llm_client or ctx.get_llm_client()
            transcribed = cast(str, await client.transcribe(local_path))
            logger.info(f"Audio transcription completed: {len(transcribed)} characters")
        except Exception:
            logger.exception("Audio transcription failed for %s", local_path)
            return None
        else:
            return transcribed

    if file_ext in TEXT_EXTENSIONS:
        path_obj = pathlib.Path(local_path)
        try:
            text_content = path_obj.read_text(encoding="utf-8")
            logger.info(f"Read pre-transcribed text file: {len(text_content)} characters")
        except Exception:
            logger.exception("Failed to read text file %s", local_path)
            return None
        else:
            return text_content

    logger.warning(f"Unknown audio file type: {file_ext}, skipping transcription")
    return None
