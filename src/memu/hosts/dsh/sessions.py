"""DSH 会话转录: ``~/.dsh/memu/transcripts/<encoded-cwd>/<session-id>.jsonl``.

DSH 自己的会话日志是多帧 zstd (``session.v4.jsonl.zstd``, 每次 append 一帧),
Python 侧读它既需要额外依赖, 又要自己切帧. 所以这里的 "原生日志" 由 memU 树内的
``dsh-memu`` 插件负责导出: 插件订阅 harness 的会话事件流, 把每个会话投影成
**规范形状**的 JSONL. 本适配器只认这份投影, 因此只覆写 :meth:`classify` --
这正是 :class:`~memu.hosts.base.TranscriptSource` 定义的那个唯一 seam.

投影记录的三种形状 (每行一个 JSON 对象)::

    {"type": "message",     "role": "user"|"assistant", "text": "...", "seq": 1, "timestamp": "..."}
    {"type": "tool_call",   "name": "...", "arguments": {...},        "seq": 2, "timestamp": "..."}
    {"type": "tool_result", "name": "...", "content": "...", "is_error": false, "seq": 3, "timestamp": "..."}

时间戳是 ISO-8601 (UTC) 字符串, 因此基类的 :meth:`TranscriptSource.timestamp`
默认实现可直接读取 ``timestamp`` 字段; 文件以会话 id 命名, 因此
:meth:`TranscriptSource.session_id` 的 ``path.stem`` 默认实现同样成立.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

from memu.hosts.base import RecordKind, TranscriptSource

TRANSCRIPTS_DIR = "~/.dsh/memu/transcripts"

_MESSAGE_TYPE = "message"
_TOOL_TYPES = frozenset({"tool_call", "tool_result"})


class DshTranscriptSource(TranscriptSource):
    """读取 ``dsh-memu`` 插件为每个 DSH 会话写出的投影。"""

    name: ClassVar[str] = "dsh"

    def __init__(self, session_dir: str | Path = TRANSCRIPTS_DIR) -> None:
        self._root = Path(session_dir).expanduser()

    def root(self) -> Path:
        return self._root

    def classify(self, record: str) -> RecordKind:
        """按投影类型分流: 对话进两条转录, 工具活动只进完整转录, 其余丢弃."""
        try:
            entry = json.loads(record)
        except json.JSONDecodeError:
            return RecordKind.OTHER
        if not isinstance(entry, dict):
            return RecordKind.OTHER
        record_type = entry.get("type")
        if record_type == _MESSAGE_TYPE:
            return RecordKind.MESSAGE
        if record_type in _TOOL_TYPES:
            return RecordKind.TOOL
        return RecordKind.OTHER
