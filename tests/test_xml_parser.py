"""
Tests for _parse_memory_element in MemorizeMixin.

Verifies that memory items with empty `<categories>` are preserved
(the prompts in src/memu/prompts/memory_type/ allow empty categories).
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
