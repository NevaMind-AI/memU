from __future__ import annotations

import json
from typing import Any


def format_conversation_for_preprocess(raw_text: str) -> str:
    """
    Normalize a conversation into a line-based format suitable for LLM preprocessing prompts.

    Supported input formats:
    - A JSON list of messages: [{"role": "...", "content": "...", "created_at": "..."}]
    - A JSON dict with a "content" list: {"content": [ ...messages... ]}

    Output format:
    - One message per line
    - Each line starts with an index marker: "[{idx}]"
    - If a created_at is available, it is included after the index
    - The role is included in square brackets: "[user]" / "[assistant]" etc.

    Notes:
    - This function expects conversation data to be JSON.
    - Newlines in message content are collapsed to spaces to keep one message per line.
    """
    stripped = (raw_text or "").strip()
    if not stripped:
        return ""

    parsed = _try_parse_json(stripped)
    if parsed is None:
        # Conversation inputs are expected to be JSON. If invalid, return original text.
        return raw_text
    messages = _extract_messages(parsed)
    if messages is None:
        return raw_text
    return _format_messages(messages)


def _try_parse_json(text: str) -> Any | None:
    if not text:
        return None
    if not (text.startswith("[") or text.startswith("{")):
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _extract_messages(payload: Any) -> list[dict[str, Any]] | None:
    if isinstance(payload, list):
        return [m for m in payload if isinstance(m, dict)]
    if isinstance(payload, dict):
        content = payload.get("content")
        if isinstance(content, list):
            return [m for m in content if isinstance(m, dict)]
    return None


def _format_messages(messages: list[dict[str, Any]]) -> str:
    out: list[str] = []
    for idx, msg in enumerate(messages):
        role = str(msg.get("role") or "user").strip() or "user"
        content = msg.get("content")
        text = _extract_text_content(content)
        created_at = _extract_created_at(msg)
        created_part = f"{created_at} " if created_at else ""
        out.append(f"[{idx}] {created_part}[{role}]: {text}")
    return "\n".join(out)


def _extract_text_content(content: Any) -> str:
    if isinstance(content, dict):
        text = content.get("text", "")
    elif isinstance(content, str):
        text = content
    else:
        text = "" if content is None else str(content)
    # Ensure single-line to keep indexing consistent
    return " ".join(str(text).splitlines()).strip()


def _extract_created_at(msg: dict[str, Any]) -> str | None:
    raw = msg.get("created_at")
    if raw is None:
        return None

    s = str(raw).strip()
    return s or None
