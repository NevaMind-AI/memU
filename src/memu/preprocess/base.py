"""Shared types and parsing helpers for resource preprocessing.

Preprocessors turn a fetched resource (text and/or a local file) into a list of
``{"text", "caption"}`` segments that downstream memory extraction consumes.
Each modality (conversation, document, video, image, audio) has its own
implementation under this package; :mod:`memu.preprocess` wires them together.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, ClassVar

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
