from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any
from xml.etree.ElementTree import Element

import defusedxml.ElementTree as ET

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable


class MemorizeParseMixin:
    """Stateless parsers for memorize LLM outputs (XML/JSON/tagged text).

    Split out of :class:`MemorizeMixin` to keep the memorize flow focused on
    orchestration. Composed onto ``MemoryService``; the only external dependency
    (``_extract_json_blob``) is resolved at runtime via the service instance.
    """

    if TYPE_CHECKING:
        _extract_json_blob: Callable[[str], str]

    def _parse_conversation_preprocess(self, raw: str) -> tuple[str | None, str | None]:
        conversation = self._extract_tag_content(raw, "conversation")
        summary = self._extract_tag_content(raw, "summary")
        return conversation, summary

    def _parse_multimodal_response(self, raw: str, content_tag: str, caption_tag: str) -> tuple[str | None, str | None]:
        """
        Parse multimodal preprocessing response (video, image, document, audio).
        Extracts content and caption from XML-like tags.

        Args:
            raw: Raw LLM response
            content_tag: Tag name for main content (e.g., "detailed_description", "processed_content")
            caption_tag: Tag name for caption (typically "caption")

        Returns:
            Tuple of (content, caption)
        """
        content = self._extract_tag_content(raw, content_tag)
        caption = self._extract_tag_content(raw, caption_tag)

        # Fallback: if no tags found, try to use raw response as content
        if not content:
            content = raw.strip()

        # Fallback for caption: use first sentence of content if no caption found
        if not caption and content:
            first_sentence = content.split(".")[0]
            caption = first_sentence if len(first_sentence) <= 200 else first_sentence[:200]

        return content, caption

    def _parse_conversation_preprocess_with_segments(
        self, raw: str, original_text: str
    ) -> tuple[str | None, list[dict[str, int | str]] | None]:
        """
        Parse conversation preprocess response and extract segments.
        Returns: (conversation_text, segments)
        """
        conversation = self._extract_tag_content(raw, "conversation")
        segments = self._extract_segments_with_fallback(raw)
        return conversation, segments

    def _extract_segments_with_fallback(self, raw: str) -> list[dict[str, int | str]] | None:
        segments = self._segments_from_json_payload(raw)
        if segments is not None:
            return segments
        try:
            blob = self._extract_json_blob(raw)
        except Exception:
            logging.exception("Failed to extract segments from conversation preprocess response")
            return None
        return self._segments_from_json_payload(blob)

    def _segments_from_json_payload(self, payload: str) -> list[dict[str, int | str]] | None:
        try:
            parsed = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            return None
        return self._segments_from_parsed_data(parsed)

    @staticmethod
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

    @staticmethod
    def _extract_tag_content(raw: str, tag: str) -> str | None:
        pattern = re.compile(rf"<{tag}>(.*?)</{tag}>", re.IGNORECASE | re.DOTALL)
        match = pattern.search(raw)
        if not match:
            return None
        content = match.group(1).strip()
        return content or None

    def _parse_memory_type_response(self, raw: str) -> list[dict[str, Any]]:
        if not raw:
            return []
        raw = raw.strip()
        if not raw:
            return []
        payload = None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            try:
                blob = self._extract_json_blob(raw)
                payload = json.loads(blob)
            except Exception:
                return []
        if not isinstance(payload, dict):
            return []
        items = payload.get("memories_items")
        if not isinstance(items, list):
            return []
        normalized: list[dict[str, Any]] = []
        for entry in items:
            if not isinstance(entry, dict):
                continue
            normalized.append(entry)
        return normalized

    def _find_xml_boundaries(self, raw: str) -> tuple[int, int, str] | None:
        """Find the start index, end index, and closing tag for XML root element."""
        root_tags = ["item", "profile", "behaviors", "events", "knowledge", "skills"]
        for tag in root_tags:
            opening = f"<{tag}>"
            closing = f"</{tag}>"
            start_idx = raw.find(opening)
            if start_idx != -1:
                end_idx = raw.rfind(closing)
                if end_idx != -1:
                    return (start_idx, end_idx, closing)
        return None

    def _parse_memory_element(self, memory_elem: Element) -> dict[str, Any] | None:
        """Parse a single memory XML element into a dict."""
        memory_dict: dict[str, Any] = {}

        content_elem = memory_elem.find("content")
        if content_elem is not None and content_elem.text:
            memory_dict["content"] = content_elem.text.strip()

        categories_elem = memory_elem.find("categories")
        if categories_elem is not None:
            categories = [cat_elem.text.strip() for cat_elem in categories_elem.findall("category") if cat_elem.text]
            memory_dict["categories"] = categories

        if memory_dict.get("content") and memory_dict.get("categories"):
            return memory_dict
        return None

    def _parse_memory_type_response_xml(self, raw: str) -> list[dict[str, Any]]:
        """
        Parse XML memory extraction output into a list of memory items.

        Expected XML format (root tag varies by memory type):
        <profile|behaviors|events|knowledge|skills>
            <memory>
                <content>...</content>
                <categories>
                    <category>...</category>
                </categories>
            </memory>
        </...>
        """
        if not raw or not raw.strip():
            return []
        raw = raw.strip()

        try:
            boundaries = self._find_xml_boundaries(raw)
            if boundaries is None:
                logger.warning("Could not find valid root tag in XML response")
                return []

            start_idx, end_idx, end_tag = boundaries
            xml_content = raw[start_idx : end_idx + len(end_tag)]
            xml_content = xml_content.replace("&", "&amp;")

            try:
                root = ET.fromstring(xml_content)
            except ET.ParseError:
                # Some LLMs emit one <item> per memory rather than a single root
                # element wrapping all memories, resulting in "junk after document
                # element" when the slice contains multiple top-level tags.  Wrap
                # the content in a synthetic root element and retry.
                root = ET.fromstring(f"<_root_>{xml_content}</_root_>")

            result: list[dict[str, Any]] = []

            for memory_elem in root.iter("memory"):
                parsed = self._parse_memory_element(memory_elem)
                if parsed:
                    result.append(parsed)

        except ET.ParseError:
            logger.exception("Failed to parse XML")
            return []
        else:
            return result
