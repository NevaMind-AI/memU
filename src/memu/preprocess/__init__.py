"""Resource preprocessing, split by format/modality.

This package extracts the per-format preprocessing logic out of the memorize
flow. Each modality has a dedicated :class:`~memu.preprocess.base.Preprocessor`
implementation, and :func:`preprocess_resource` dispatches to the right one based
on the resource modality.
"""

from __future__ import annotations

from typing import Any

from memu.preprocess.audio import AudioPreprocessor, prepare_audio_text
from memu.preprocess.base import (
    PreprocessContext,
    Preprocessor,
    PreprocessResult,
    parse_multimodal_response,
)
from memu.preprocess.conversation import ConversationPreprocessor
from memu.preprocess.document import DocumentPreprocessor
from memu.preprocess.image import ImagePreprocessor
from memu.preprocess.video import VideoPreprocessor
from memu.prompts.preprocess import PROMPTS as PREPROCESS_PROMPTS

# Registry mapping modality -> preprocessor. Register new formats here.
PREPROCESSORS: dict[str, Preprocessor] = {
    ConversationPreprocessor.modality: ConversationPreprocessor(),
    VideoPreprocessor.modality: VideoPreprocessor(),
    ImagePreprocessor.modality: ImagePreprocessor(),
    DocumentPreprocessor.modality: DocumentPreprocessor(),
    AudioPreprocessor.modality: AudioPreprocessor(),
}

__all__ = [
    "PREPROCESSORS",
    "AudioPreprocessor",
    "ConversationPreprocessor",
    "DocumentPreprocessor",
    "ImagePreprocessor",
    "PreprocessContext",
    "PreprocessResult",
    "Preprocessor",
    "VideoPreprocessor",
    "parse_multimodal_response",
    "preprocess_resource",
]


def _resolve_template(modality: str, ctx: PreprocessContext) -> str | None:
    configured_prompt = ctx.multimodal_preprocess_prompts.get(modality)
    if configured_prompt is None:
        return PREPROCESS_PROMPTS.get(modality)
    if isinstance(configured_prompt, str):
        return configured_prompt
    # No custom prompts configured for preprocessing for now. If the user decides
    # to use their custom prompt, they must provide ALL prompt blocks.
    return ctx.resolve_custom_prompt(configured_prompt, {})


async def preprocess_resource(
    *,
    modality: str,
    local_path: str,
    text: str | None,
    ctx: PreprocessContext,
    llm_client: Any | None = None,
) -> PreprocessResult:
    """Preprocess a resource based on its modality.

    - Text-based modalities (conversation, document): require text content.
    - Audio: transcribe (or read sidecar text) first, then process as text.
    - Media modalities (video, image): process media files directly.

    Returns a list of preprocessed resources, each with ``text`` and ``caption``.
    """
    template = _resolve_template(modality, ctx)
    if not template:
        return [{"text": text, "caption": None}]

    if modality == "audio":
        text = await prepare_audio_text(local_path, text, ctx, llm_client=llm_client)
        if text is None:
            return [{"text": None, "caption": None}]

    preprocessor = PREPROCESSORS.get(modality)
    if preprocessor is None:
        return [{"text": text, "caption": None}]

    if preprocessor.requires_text and not text:
        return [{"text": text, "caption": None}]

    return await preprocessor.run(
        local_path=local_path,
        text=text,
        template=template,
        ctx=ctx,
        llm_client=llm_client,
    )
