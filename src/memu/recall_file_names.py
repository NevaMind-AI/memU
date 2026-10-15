from __future__ import annotations

import re


def canonical_recall_file_name(name: str) -> str:
    """Normalize case and separators without imposing a Unicode character whitelist."""
    normalized = re.sub(r"[\s_-]+", "-", name.strip().lower()).strip("-")
    if any(char in normalized for char in "/\\\x00") or normalized in {".", ".."}:
        msg = "recall-file name must not contain path separators or null bytes"
        raise ValueError(msg)
    return normalized
