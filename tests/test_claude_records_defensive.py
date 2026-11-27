"""Malformed content-block metadata must not halt Claude transcript preparation."""

import json

from memu.hosts.base import RecordKind
from memu.hosts.claude_records import classify_claude_record


def _record(blocks: list[dict[str, object]]) -> str:
    return json.dumps({"type": "assistant", "message": {"content": blocks}})


def test_unhashable_block_type_is_ignored() -> None:
    assert classify_claude_record(_record([{"type": ["text"]}])) is RecordKind.OTHER
    assert classify_claude_record(_record([{"type": ["text"]}, {"type": "tool_use"}])) is RecordKind.TOOL
    assert (
        classify_claude_record(_record([{"type": {"unexpected": "text"}}, {"type": "text", "text": "hello"}]))
        is RecordKind.MESSAGE
    )
