"""
Utilities for handling memory item references in category summaries.

References are inline citations in the format [ref:ITEM_ID] that link
specific statements in category summaries to their source memory items.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from memu.database.interfaces import Database

# Pattern to match references like [ref:abc123] or [ref:abc123,def456]
REFERENCE_PATTERN = re.compile(r"\[ref:([a-zA-Z0-9_,\-]+)\]")


def extract_references(text: str | None) -> list[str]:
    """
    Extract all item IDs referenced in a text.

    Args:
        text: Text containing [ref:ITEM_ID] citations

    Returns:
        List of unique item IDs found in references

    Example:
        >>> extract_references("User loves coffee [ref:abc123]. Also tea [ref:def456].")
        ['abc123', 'def456']
    """
    if not text:
        return []

    item_ids: list[str] = []
    seen: set[str] = set()

    for match in REFERENCE_PATTERN.finditer(text):
        # Handle comma-separated IDs like [ref:abc,def]
        ids_str = match.group(1)
        for item_id in ids_str.split(","):
            item_id = item_id.strip()
            if item_id and item_id not in seen:
                item_ids.append(item_id)
                seen.add(item_id)

    return item_ids


def strip_references(text: str | None) -> str | None:
    """
    Remove all [ref:...] citations from text for clean display.

    Args:
        text: Text containing references

    Returns:
        Text with references removed

    Example:
        >>> strip_references("User loves coffee [ref:abc123].")
        'User loves coffee.'
    """
    if not text:
        return text
    # Remove references
    result = REFERENCE_PATTERN.sub("", text)
    # Clean up space before punctuation (e.g., " ." -> ".")
    result = re.sub(r"\s+([.,;:!?])", r"\1", result)
    # Collapse multiple spaces into one and strip
    result = " ".join(result.split())
    return result


def format_references_as_citations(text: str | None) -> str | None:
    """
    Convert [ref:ID] format to numbered citations [1], [2], etc.

    Args:
        text: Text with [ref:ID] references

    Returns:
        Text with numbered citations and a reference list at the end

    Example:
        >>> format_references_as_citations("User loves coffee [ref:abc].")
        'User loves coffee [1].\\n\\nReferences:\\n[1] abc'
    """
    if not text:
        return text

    refs = extract_references(text)
    if not refs:
        return text

    # Build ID to number mapping
    id_to_num = {ref_id: idx + 1 for idx, ref_id in enumerate(refs)}

    # Replace [ref:ID] with [N]
    def replace_ref(match: re.Match) -> str:
        ids_str = match.group(1)
        nums = []
        for item_id in ids_str.split(","):
            item_id = item_id.strip()
            if item_id in id_to_num:
                nums.append(str(id_to_num[item_id]))
        return f"[{','.join(nums)}]" if nums else ""

    result = REFERENCE_PATTERN.sub(replace_ref, text)

    # Add reference list at end
    ref_list = "\n".join(f"[{num}] {ref_id}" for ref_id, num in id_to_num.items())
    return f"{result}\n\nReferences:\n{ref_list}"


def fetch_referenced_items(
    text: str,
    store: Database,
) -> list[dict]:
    """
    Fetch memory items referenced in text.

    Args:
        text: Text containing [ref:ITEM_ID] citations
        store: Database store instance

    Returns:
        List of memory item dicts with id, summary, memory_type
    """
    item_ids = extract_references(text)
    if not item_ids:
        return []

    items = []
    for item_id in item_ids:
        item = store.memory_item_repo.get_item(item_id)
        if item:
            items.append({
                "id": item.id,
                "summary": item.summary,
                "memory_type": item.memory_type,
            })

    return items


def build_item_reference_map(items: list[tuple[str, str]]) -> str:
    """
    Build a reference map string for the LLM prompt.

    Args:
        items: List of (item_id, summary) tuples

    Returns:
        Formatted string showing available item IDs

    Example:
        >>> build_item_reference_map([("abc", "User loves coffee")])
        'Available memory items for reference:\\n- [ref:abc] User loves coffee'
    """
    if not items:
        return ""

    lines = ["Available memory items for reference:"]
    for item_id, summary in items:
        # Truncate long summaries
        display = summary[:100] + "..." if len(summary) > 100 else summary
        lines.append(f"- [ref:{item_id}] {display}")

    return "\n".join(lines)
