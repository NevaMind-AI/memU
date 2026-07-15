"""The generic host: any agent's JSONL session log, dialect sniffed per record.

The five dedicated adapters each hard-code one host's log schema. This source
covers *everyone else*: agents whose transcripts are JSONL in one of the shapes
the ecosystem has converged on. Every record is classified by trying the known
dialects in order — the shapes are mutually exclusive enough that the first
match is the right one:

1. **payload-wrapped** (Codex lineage): ``{"payload": {"type": "message", "role": …}}``
2. **typed message tree** (OpenClaw/pi lineage): ``{"type": "message", "message": {"role": …}}``
3. **typed block records** (Claude Code lineage): ``{"type": "user"|"assistant",
   "message": {"content": [blocks]}}`` — the block type decides, because tool
   results ride in user-typed records
4. **role + message** (Cursor lineage): ``{"role": …, "message": {"content": [blocks]}}``
5. **flat chat rows** (OpenAI-client lineage, what most new agents log):
   ``{"role": …, "content": …, "tool_calls": …}``

A record matching no dialect is noise — exactly what the dedicated adapters do
with their hosts' metadata records, and what keeps a half-recognized log safe:
the mining jobs see only what provably is conversation or tool traffic.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, ClassVar

from memu.hosts.base import RecordKind, TranscriptSource

_MESSAGE_ROLES = ("user", "assistant")


def _from_epoch(value: float) -> str:
    seconds = value / 1000 if value > 1e11 else value
    return datetime.datetime.fromtimestamp(seconds, tz=datetime.UTC).isoformat()


def _classify_blocks(content: Any, *, meta: bool = False) -> RecordKind | None:
    """Shared verdict for block-list content (dialects 3 and 4)."""
    if isinstance(content, str):
        return RecordKind.OTHER if meta else RecordKind.MESSAGE
    if not isinstance(content, list):
        return None
    kinds = {block.get("type") for block in content if isinstance(block, dict)}
    if "text" in kinds:
        return RecordKind.OTHER if meta else RecordKind.MESSAGE
    if kinds & {"tool_use", "tool_result", "toolCall", "tool_call"}:
        return RecordKind.TOOL
    return RecordKind.OTHER


def _classify_payload_wrapped(payload: dict[str, Any]) -> RecordKind:
    """Dialect 1: the Codex lineage's ``{"payload": {...}}`` wrapper."""
    kind = payload.get("type")
    if kind == "message" and payload.get("role") in _MESSAGE_ROLES:
        return RecordKind.MESSAGE
    if isinstance(kind, str) and ("function_call" in kind or "tool" in kind):
        return RecordKind.TOOL
    return RecordKind.OTHER


def _classify_message_tree(message: dict[str, Any]) -> RecordKind:
    """Dialect 2: the OpenClaw/pi lineage's ``{"type": "message", "message": {...}}``."""
    role = message.get("role")
    if role in _MESSAGE_ROLES:
        return RecordKind.MESSAGE
    if role in ("toolResult", "tool"):
        return RecordKind.TOOL
    return RecordKind.OTHER


def _classify_flat_row(entry: dict[str, Any]) -> RecordKind:
    """Dialect 5: flat OpenAI-client chat rows — role and content at the top level."""
    role = entry.get("role")
    if role == "tool" or entry.get("tool_call_id"):
        return RecordKind.TOOL
    if role in _MESSAGE_ROLES:
        if entry.get("content"):
            verdict = _classify_blocks(entry.get("content"))
            return verdict if verdict is not None else RecordKind.MESSAGE
        if entry.get("tool_calls"):
            return RecordKind.TOOL
    return RecordKind.OTHER


class GenericTranscriptSource(TranscriptSource):
    """Any agent's JSONL session directory; the record dialect is sniffed."""

    name: ClassVar[str] = "agent"

    def __init__(self, session_dir: str | Path) -> None:
        import os

        self._root = Path(os.path.expanduser(str(session_dir)))

    def root(self) -> Path:
        return self._root

    def classify(self, record: str) -> RecordKind:
        try:
            entry = json.loads(record)
        except json.JSONDecodeError:
            return RecordKind.OTHER
        if not isinstance(entry, dict):
            return RecordKind.OTHER

        payload = entry.get("payload")
        if isinstance(payload, dict):
            return _classify_payload_wrapped(payload)

        message = entry.get("message")
        entry_type = entry.get("type")
        if entry_type == "message" and isinstance(message, dict):
            return _classify_message_tree(message)
        if entry_type in _MESSAGE_ROLES and isinstance(message, dict):
            verdict = _classify_blocks(message.get("content"), meta=bool(entry.get("isMeta")))
            return verdict if verdict is not None else RecordKind.OTHER
        if entry.get("role") in _MESSAGE_ROLES and isinstance(message, dict):
            verdict = _classify_blocks(message.get("content"))
            return verdict if verdict is not None else RecordKind.OTHER
        return _classify_flat_row(entry)

    def timestamp(self, record: str) -> str | None:
        """``timestamp`` wherever the dialect puts it; ISO strings and epochs both."""
        try:
            entry = json.loads(record)
        except json.JSONDecodeError:
            return None
        if not isinstance(entry, dict):
            return None

        value = entry.get("timestamp")
        if value is None and isinstance(entry.get("payload"), dict):
            value = entry["payload"].get("timestamp")
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            return _from_epoch(value)
        return None
