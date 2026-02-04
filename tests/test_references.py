"""
Tests for memory item reference functionality (Issue #202).

Tests cover:
1. Reference extraction from text
2. Reference stripping for clean display
3. Reference formatting as citations
4. Reference-aware category summary generation
5. Reference-aware retrieval
"""

from __future__ import annotations

from memu.utils.references import (
    build_item_reference_map,
    extract_references,
    format_references_as_citations,
    strip_references,
)


class TestExtractReferences:
    """Tests for extract_references function."""

    def test_extract_single_reference(self):
        """Should extract a single reference ID."""
        text = "User loves coffee [ref:abc123]."
        refs = extract_references(text)
        assert refs == ["abc123"]

    def test_extract_multiple_references(self):
        """Should extract multiple reference IDs in order."""
        text = "User loves coffee [ref:abc123]. Also tea [ref:def456]."
        refs = extract_references(text)
        assert refs == ["abc123", "def456"]

    def test_extract_comma_separated_references(self):
        """Should handle comma-separated IDs in single reference."""
        text = "User prefers hot drinks [ref:abc,def,ghi]."
        refs = extract_references(text)
        assert refs == ["abc", "def", "ghi"]

    def test_extract_no_duplicates(self):
        """Should not return duplicate IDs."""
        text = "Coffee [ref:abc]. More coffee [ref:abc]. Tea [ref:def]."
        refs = extract_references(text)
        assert refs == ["abc", "def"]

    def test_extract_empty_text(self):
        """Should return empty list for empty text."""
        assert extract_references("") == []
        assert extract_references(None) == []

    def test_extract_no_references(self):
        """Should return empty list when no references present."""
        text = "User loves coffee and tea."
        refs = extract_references(text)
        assert refs == []

    def test_extract_with_hyphens_and_underscores(self):
        """Should handle IDs with hyphens and underscores."""
        text = "Info [ref:item_abc-123]."
        refs = extract_references(text)
        assert refs == ["item_abc-123"]


class TestStripReferences:
    """Tests for strip_references function."""

    def test_strip_single_reference(self):
        """Should remove single reference."""
        text = "User loves coffee [ref:abc123]."
        result = strip_references(text)
        assert result == "User loves coffee."

    def test_strip_multiple_references(self):
        """Should remove all references."""
        text = "Coffee [ref:abc]. Tea [ref:def]."
        result = strip_references(text)
        assert result == "Coffee. Tea."

    def test_strip_comma_separated(self):
        """Should remove comma-separated references."""
        text = "Drinks [ref:abc,def,ghi]."
        result = strip_references(text)
        assert result == "Drinks."

    def test_strip_empty_text(self):
        """Should handle empty text."""
        assert strip_references("") == ""
        assert strip_references(None) is None

    def test_strip_no_references(self):
        """Should return text unchanged if no references."""
        text = "User loves coffee."
        result = strip_references(text)
        assert result == "User loves coffee."


class TestFormatReferencesAsCitations:
    """Tests for format_references_as_citations function."""

    def test_format_single_citation(self):
        """Should convert single reference to numbered citation."""
        text = "User loves coffee [ref:abc]."
        result = format_references_as_citations(text)
        assert result is not None
        assert "[1]" in result
        assert "[ref:abc]" not in result
        assert "References:" in result
        assert "[1] abc" in result

    def test_format_multiple_citations(self):
        """Should number citations in order of appearance."""
        text = "Coffee [ref:abc]. Tea [ref:def]."
        result = format_references_as_citations(text)
        assert result is not None
        assert "[1]" in result
        assert "[2]" in result
        assert "[1] abc" in result
        assert "[2] def" in result

    def test_format_empty_text(self):
        """Should handle empty text."""
        assert format_references_as_citations("") == ""
        assert format_references_as_citations(None) is None

    def test_format_no_references(self):
        """Should return text unchanged if no references."""
        text = "User loves coffee."
        result = format_references_as_citations(text)
        assert result == text


class TestBuildItemReferenceMap:
    """Tests for build_item_reference_map function."""

    def test_build_map_single_item(self):
        """Should format single item reference."""
        items = [("abc123", "User loves coffee")]
        result = build_item_reference_map(items)
        assert "Available memory items for reference:" in result
        assert "[ref:abc123]" in result
        assert "User loves coffee" in result

    def test_build_map_multiple_items(self):
        """Should format multiple item references."""
        items = [
            ("abc", "User loves coffee"),
            ("def", "User prefers tea"),
        ]
        result = build_item_reference_map(items)
        assert "[ref:abc]" in result
        assert "[ref:def]" in result

    def test_build_map_truncates_long_summaries(self):
        """Should truncate summaries longer than 100 chars."""
        long_summary = "x" * 150
        items = [("abc", long_summary)]
        result = build_item_reference_map(items)
        assert "..." in result
        assert len(result.split("\n")[1]) < 150

    def test_build_map_empty_list(self):
        """Should return empty string for empty list."""
        assert build_item_reference_map([]) == ""


class TestReferenceIntegration:
    """Integration tests for reference functionality."""

    def test_roundtrip_extract_and_strip(self):
        """Extracting then stripping should give clean text."""
        original = "User loves coffee [ref:abc]. Tea [ref:def]."
        refs = extract_references(original)
        clean = strip_references(original)

        assert refs == ["abc", "def"]
        assert clean is not None
        assert "[ref:" not in clean
        assert "coffee" in clean
        assert "Tea" in clean

    def test_citation_preserves_content(self):
        """Citation formatting should preserve text content."""
        original = "User loves coffee [ref:abc]."
        result = format_references_as_citations(original)

        assert result is not None
        assert "User loves coffee" in result
        assert "abc" in result  # ID should be in references section
