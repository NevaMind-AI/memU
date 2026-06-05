from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


SUPPORTED_FILTER_OPERATORS = frozenset({"in"})


def split_filter_key(raw_key: Any) -> tuple[str, str | None]:
    """Split and validate a filter key.

    Supported filters are equality (`field`) and membership (`field__in`).
    """

    if not isinstance(raw_key, str) or not raw_key.strip():
        msg = "Filter field must be a non-empty string"
        raise ValueError(msg)

    key = raw_key.strip()
    field, separator, operator = key.partition("__")
    if not field:
        msg = "Filter field must be a non-empty string"
        raise ValueError(msg)
    if not separator:
        return field, None
    if operator not in SUPPORTED_FILTER_OPERATORS:
        msg = f"Unsupported filter operator '__{operator}' for field '{field}'"
        raise ValueError(msg)
    return field, operator


def normalize_filter_value(field: str, operator: str | None, expected: Any) -> Any:
    """Normalize a filter value after its key has been validated."""

    if operator != "in":
        return expected
    if isinstance(expected, str):
        return expected
    if isinstance(expected, Mapping):
        msg = f"Filter '{field}__in' must be a string or an iterable of values"
        raise ValueError(msg)
    if not isinstance(expected, Iterable):
        msg = f"Filter '{field}__in' must be a string or an iterable of values"
        raise ValueError(msg)
    return tuple(expected)


def build_filter_key(field: str, operator: str | None) -> str:
    return field if operator is None else f"{field}__{operator}"


__all__ = [
    "SUPPORTED_FILTER_OPERATORS",
    "build_filter_key",
    "normalize_filter_value",
    "split_filter_key",
]
