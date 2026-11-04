"""Shared in-memory evaluation of repository filters."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _matches_value(actual: Any, expected: Any, op: str | None) -> bool:
    if op == "isnull":
        return bool((actual is None) == expected)
    if op != "in" or isinstance(expected, str):
        return bool(actual == expected)
    try:
        return actual in expected
    except TypeError:
        return False


def matches_where(obj: Any, where: Mapping[str, Any] | None) -> bool:
    for key, expected in (where or {}).items():
        if expected is None:
            continue
        field, _, op = key.partition("__")
        if not _matches_value(getattr(obj, field, None), expected, op):
            return False
    return True
