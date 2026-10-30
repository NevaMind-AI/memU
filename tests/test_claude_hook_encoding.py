"""Claude hook pipes use UTF-8 independently of the process locale."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("encoding", ["ascii:surrogateescape", "gbk"])
@pytest.mark.parametrize("command", ["prompt-hook", "memorize-hook"])
def test_utf8_hook_pipes(tmp_path, encoding, command):
    script = """
import json, subprocess, sys
from memu.hosts.claude_code import memorize_hook, prompt_hook
from memu.hosts.claude_code.cli import main
original_load = json.load
calls = []
def load(stream, *args, **kwargs):
    value = original_load(stream, *args, **kwargs)
    if stream is sys.stdin:
        assert value['prompt'] == '余时遗物架构😀'
        calls.append('input')
    return value
json.load = load
def retrieve(argv, **kwargs):
    assert kwargs['input'].decode('utf-8') == '余时遗物架构😀'
    payload = {'hits': [{'text': '中文记忆😀'}], 'resources': []}
    return subprocess.CompletedProcess(argv, 0, json.dumps(payload, ensure_ascii=False).encode('utf-8'), b'')
prompt_hook.subprocess.run = retrieve
memorize_hook.launch_background = lambda args: calls.append('launch')
command, base = sys.argv[1:]
args = [command, '--base-dir', base]
if command == 'memorize-hook':
    args += ['--agent', 'unused']
assert main(args) == 0
assert 'input' in calls
if command == 'memorize-hook':
    assert 'launch' in calls
"""
    env = {**os.environ, "PYTHONIOENCODING": encoding}
    env.pop("MEMU_CLAUDE_MEMORIZE", None)
    event = {"hook_event_name": "UserPromptSubmit", "prompt": "余时遗物架构😀"}
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script, command, str(tmp_path)],
        input=json.dumps(event, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        timeout=10,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    output = json.loads(result.stdout.decode("utf-8"))
    if command == "prompt-hook":
        assert "中文记忆😀" in output["hookSpecificOutput"]["additionalContext"]
    else:
        assert output == {}
