from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any


def compute_content_hash(summary: str, memory_type: str) -> str:
    """
    Generate a stable hash for memory deduplication.

    The normalization intentionally matches the salience/reinforcement content
    hash used by storage backends: lowercase, trim, and collapse whitespace.
    """
    normalized = " ".join(summary.lower().split())
    content = f"{memory_type}:{normalized}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def dedupe_resource_plans(resource_plans: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate extracted memory entries while preserving first-seen order."""
    seen_categories: dict[str, list[str]] = {}
    deduped_plans: list[dict[str, Any]] = []

    for plan in resource_plans:
        next_plan = dict(plan)
        next_entries: list[tuple[str, str, list[str]]] = []
        for raw_entry in plan.get("entries") or []:
            normalized_entry = normalize_extracted_entry(raw_entry)
            if normalized_entry is None:
                continue
            memory_type, content, categories = normalized_entry
            key = compute_content_hash(content, memory_type)
            if key in seen_categories:
                seen_categories[key][:] = merge_category_names(seen_categories[key], categories)
                continue
            next_entries.append((memory_type, content, categories))
            seen_categories[key] = categories
        next_plan["entries"] = next_entries
        deduped_plans.append(next_plan)

    return deduped_plans


def normalize_extracted_entry(raw_entry: Any) -> tuple[str, str, list[str]] | None:
    if not isinstance(raw_entry, tuple) or len(raw_entry) != 3:
        return None
    raw_memory_type, raw_content, raw_categories = raw_entry
    if not isinstance(raw_memory_type, str) or not isinstance(raw_content, str):
        return None
    content = raw_content.strip()
    if not content:
        return None
    categories = [
        category.strip()
        for category in (raw_categories or [])
        if isinstance(category, str) and category.strip()
    ]
    return raw_memory_type, content, merge_category_names([], categories)


def merge_category_names(existing: Sequence[str], incoming: Sequence[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for category in [*existing, *incoming]:
        key = category.strip().lower()
        if not key or key in seen:
            continue
        merged.append(category.strip())
        seen.add(key)
    return merged


__all__ = [
    "compute_content_hash",
    "dedupe_resource_plans",
    "merge_category_names",
    "normalize_extracted_entry",
]
