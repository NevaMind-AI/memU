"""Shared types and parsing helpers for resource preprocessing.

Preprocessors turn a fetched resource (text and/or a local file) into a list of
``{"text", "caption"}`` segments that downstream memory extraction consumes.
Each modality (conversation, document, video, image, audio) has its own
implementation under this package; :mod:`memu.preprocess` wires them together.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, ClassVar

logger = logging.getLogger(__name__)

# A preprocessed resource is a list of segments, each carrying optional text and
# an optional short caption.
PreprocessResult = list[dict[str, str | None]]


@dataclass(frozen=True)
class PreprocessContext:
    """Dependencies a preprocessor needs from the owning memory service.

    Bundled explicitly so the per-format logic stays decoupled from the large
    ``MemorizeMixin`` while preserving its exact behavior.
    """

    get_llm_client: Callable[[], Any]
    get_vlm_client: Callable[[], Any]
    escape_prompt_value: Callable[[str], str]
    extract_json_blob: Callable[[str], str]
    resolve_custom_prompt: Callable[[Any, Mapping[str, str]], str]
    multimodal_preprocess_prompts: Mapping[str, Any]


class Preprocessor:
    """Base class for modality-specific preprocessors."""

    modality: ClassVar[str] = "base"
    # Whether the modality cannot proceed without resolved text content.
    requires_text: ClassVar[bool] = False

    async def run(
        self,
        *,
        local_path: str,
        text: str | None,
        template: str,
        ctx: PreprocessContext,
        llm_client: Any | None = None,
    ) -> PreprocessResult:
        raise NotImplementedError


def extract_tag_content(raw: str, tag: str) -> str | None:
    """Extract inner text of an XML-like ``<tag>...</tag>`` block."""
    pattern = re.compile(rf"<{tag}>(.*?)</{tag}>", re.IGNORECASE | re.DOTALL)
    match = pattern.search(raw)
    if not match:
        return None
    content = match.group(1).strip()
    return content or None


def parse_multimodal_response(raw: str, content_tag: str, caption_tag: str) -> tuple[str | None, str | None]:
    """Parse a multimodal preprocessing response (video, image, document, audio).

    Extracts content and caption from XML-like tags, with fallbacks when tags are
    absent.
    """
    content = extract_tag_content(raw, content_tag)
    caption = extract_tag_content(raw, caption_tag)

    # Fallback: if no tags found, use the raw response as content.
    if not content:
        content = raw.strip()

    # Fallback for caption: use the first sentence of content if none found.
    if not caption and content:
        first_sentence = content.split(".")[0]
        caption = first_sentence if len(first_sentence) <= 200 else first_sentence[:200]

    return content, caption


def parse_conversation_segments(
    raw: str, extract_json_blob: Callable[[str], str]
) -> tuple[str | None, list[dict[str, int | str]] | None]:
    """Parse a conversation preprocess response into (conversation_text, segments)."""
    conversation = extract_tag_content(raw, "conversation")
    segments = _extract_segments_with_fallback(raw, extract_json_blob)
    return conversation, segments


def _extract_segments_with_fallback(
    raw: str, extract_json_blob: Callable[[str], str]
) -> list[dict[str, int | str]] | None:
    segments = _segments_from_json_payload(raw)
    if segments is not None:
        return segments
    try:
        blob = extract_json_blob(raw)
    except Exception:
        logger.exception("Failed to extract segments from conversation preprocess response")
        return None
    return _segments_from_json_payload(blob)


def _segments_from_json_payload(payload: str) -> list[dict[str, int | str]] | None:
    try:
        parsed = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return None
    return _segments_from_parsed_data(parsed)


def _segments_from_parsed_data(parsed: Any) -> list[dict[str, int | str]] | None:
    if not isinstance(parsed, dict):
        return None
    segments_data = parsed.get("segments")
    if not isinstance(segments_data, list):
        return None
    segments: list[dict[str, int | str]] = []
    for seg in segments_data:
        if isinstance(seg, dict) and "start" in seg and "end" in seg:
            try:
                segment: dict[str, int | str] = {
                    "start": int(seg["start"]),
                    "end": int(seg["end"]),
                }
                if "caption" in seg and isinstance(seg["caption"], str):
                    segment["caption"] = seg["caption"]
                segments.append(segment)
            except (TypeError, ValueError):
                continue
    return segments or None
