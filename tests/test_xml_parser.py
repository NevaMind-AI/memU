"""
Tests for XML memory extraction parser in MemorizeMixin.

Tests cover:
1. Memory items with empty `categories` are preserved (prompts allow empty).
2. Root-tag whitelist accepts every MemoryType value (singular and plural).
"""

from __future__ import annotations

import defusedxml.ElementTree as ET

from memu.app.memorize import MemorizeMixin


def _mixin() -> MemorizeMixin:
    return MemorizeMixin.__new__(MemorizeMixin)


class TestParseMemoryElement:
    """Tests for _parse_memory_element."""

    def test_keeps_item_with_empty_categories(self):
        """Empty <categories> tag should not cause the item to be dropped."""
        elem = ET.fromstring("<memory><content>The user prefers dark mode.</content><categories></categories></memory>")
        assert _mixin()._parse_memory_element(elem) == {
            "content": "The user prefers dark mode.",
            "categories": [],
        }

    def test_keeps_item_without_categories_tag(self):
        """Missing <categories> tag should not cause the item to be dropped."""
        elem = ET.fromstring("<memory><content>The user lives in Beijing.</content></memory>")
        assert _mixin()._parse_memory_element(elem) == {
            "content": "The user lives in Beijing.",
            "categories": [],
        }

    def test_drops_item_without_content(self):
        """Items without <content> are still dropped."""
        elem = ET.fromstring("<memory><content></content><categories><category>x</category></categories></memory>")
        assert _mixin()._parse_memory_element(elem) is None

    def test_keeps_non_empty_categories(self):
        """Non-empty <categories> is preserved verbatim."""
        elem = ET.fromstring(
            "<memory>"
            "<content>The user drinks coffee daily.</content>"
            "<categories><category>habits</category><category>preferences</category></categories>"
            "</memory>"
        )
        parsed = _mixin()._parse_memory_element(elem)
        assert parsed is not None
        assert parsed["categories"] == ["habits", "preferences"]


class TestFindXmlBoundaries:
    """Tests for _find_xml_boundaries root-tag detection."""

    def test_accepts_singular_event(self):
        raw = "<event><memory><content>x</content></memory></event>"
        boundaries = _mixin()._find_xml_boundaries(raw)
        assert boundaries is not None
        assert boundaries[2] == "</event>"

    def test_accepts_singular_behavior(self):
        raw = "<behavior><memory><content>x</content></memory></behavior>"
        assert _mixin()._find_xml_boundaries(raw) is not None

    def test_accepts_singular_skill(self):
        raw = "<skill><memory><content>x</content></memory></skill>"
        assert _mixin()._find_xml_boundaries(raw) is not None

    def test_accepts_tool(self):
        """`tool` is a valid MemoryType (database/models.py) but was missing."""
        raw = "<tool><memory><content>x</content></memory></tool>"
        assert _mixin()._find_xml_boundaries(raw) is not None

    def test_accepts_legacy_plural_tags(self):
        """Original whitelist must keep working."""
        for tag in ("profile", "behaviors", "events", "knowledge", "skills"):
            raw = f"<{tag}><memory><content>x</content></memory></{tag}>"
            assert _mixin()._find_xml_boundaries(raw) is not None, tag

    def test_rejects_unknown_root(self):
        raw = "<random><memory><content>x</content></memory></random>"
        assert _mixin()._find_xml_boundaries(raw) is None


class TestParseMemoryTypeResponseXml:
    """End-to-end tests via _parse_memory_type_response_xml."""

    def test_singular_root_with_empty_categories(self):
        """LLM returns <event> root with one item lacking categories."""
        raw = (
            "<event><memory>"
            "<content>The user attended a meetup in Beijing yesterday.</content>"
            "<categories></categories>"
            "</memory></event>"
        )
        items = _mixin()._parse_memory_type_response_xml(raw)
        assert len(items) == 1
        assert items[0]["categories"] == []

    def test_tool_root_with_mixed_categories(self):
        """Two memories under <tool>, one categorised, one not."""
        raw = (
            "<tool>"
            "<memory><content>Calculator added 2 and 2.</content>"
            "<categories><category>math</category></categories></memory>"
            "<memory><content>Weather queried for Beijing.</content>"
            "<categories></categories></memory>"
            "</tool>"
        )
        items = _mixin()._parse_memory_type_response_xml(raw)
        assert [it["categories"] for it in items] == [["math"], []]
