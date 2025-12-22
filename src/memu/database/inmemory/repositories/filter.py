from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def matches_where(obj: Any, where: Mapping[str, Any] | None) -> bool:
    """Basic field/`__in` matcher for in-memory repos."""
    if not where:
        return True
    for raw_key, expected in where.items():
        if expected is None:
            continue
        field, op = [*raw_key.split("__", 1), None][:2]
        actual = getattr(obj, str(field), None)
        if op == "in":
            if isinstance(expected, str):
                if actual != expected:
                    return False
            else:
                try:
                    if actual not in expected:
                        return False
                except TypeError:
                    return False
        else:
            if actual != expected:
                return False
    return True


__all__ = ["matches_where"]
