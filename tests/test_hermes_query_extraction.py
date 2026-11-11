"""Hermes extraction runs off the hook path and routes the selected query."""

from __future__ import annotations

import asyncio
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from typing import Any

import pytest

from memu.hosts import query_extraction
from memu.hosts.hermes import hook
from memu.hosts.hermes import query_extraction as hermes


@pytest.mark.parametrize("value", [{"query": "topic"}, {"query": ""}, {"query": "x" * 201}, "bad JSON"])
def test_extraction_uses_host_python_and_shared_runner(monkeypatch, value):
    monkeypatch.setenv("PYTHONPATH", "foreign")
    monkeypatch.setenv("PYTHONHOME", "foreign")

    def execute(argv, source, cwd, flags, **kwargs):
        assert argv[:2] == ["hermes-python", "-c"]
        assert "call_llm" in argv[2]
        assert source == b""
        assert (cwd / "request.txt").read_text(encoding="utf-8") == query_extraction.extraction_instruction("x" * 600)
        assert argv[3] == str(cwd / "request.txt")
        assert json.loads(argv[4]) == ["selected-module-path"]
        assert kwargs["env"]["MEMU_BRIDGING_RUN"] == "1"
        assert "PYTHONPATH" not in kwargs["env"] and "PYTHONHOME" not in kwargs["env"]
        assert cwd.is_dir()
        return value.encode() if isinstance(value, str) else json.dumps(value).encode()

    monkeypatch.setattr(query_extraction, "run_extraction", execute)
    trace: dict[str, Any] = {}
    assert hermes.select_query("x" * 600, trace, python="hermes-python", python_paths=["selected-module-path"]) == (
        "topic" if value == {"query": "topic"} else "x" * 600
    )


@pytest.mark.asyncio
async def test_hook_routes_extracted_query_and_logs_selection(tmp_path, monkeypatch):
    monkeypatch.setattr(hermes, "_extract", lambda text, **kwargs: "topic at end")

    async def retrieve(query, *, query_kind):
        assert (query, query_kind) == ("topic at end", "extracted")
        return {"hits": [], "resources": []}

    monkeypatch.setattr(hook, "retrieve", retrieve)
    await hook.retrieve_context(tmp_path, {"prompt": "x" * 2500, "hermes_python": "host-python"})
    trace = json.loads(next((tmp_path / "log/hooks/retrieve").glob("*.json")).read_text(encoding="utf-8"))
    assert trace["query_source"] == "extracted"
    assert trace["extraction_status"] == "succeeded"
    assert trace["query_truncated"] is False


@pytest.mark.parametrize("managed_dependencies", [False, True])
@pytest.mark.parametrize("host_paths", [False, True])
def test_query_worker_uses_configured_runtime_without_tools(monkeypatch, tmp_path, managed_dependencies, host_paths):
    from memu.hosts.hermes import query_worker

    runtime = {"provider": "custom", "base_url": "http://local", "api_key": "test", "api_mode": "chat_completions"}

    def resolve(**kwargs):
        assert kwargs == {"requested": "custom", "target_model": "configured-model"}
        return runtime

    def call(**kwargs):
        assert kwargs["model"] == "configured-model"
        assert kwargs["main_runtime"] is runtime
        assert kwargs["base_url"] == "http://local" and kwargs["api_key"] == "test"
        assert kwargs["tools"] is None and kwargs["timeout"] == 12
        assert kwargs["messages"][0]["role"] == "system"
        assert kwargs["messages"][1] == {"role": "user", "content": "instruction"}
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"query":"topic"}'))])

    activated: list[Any] = []
    monkeypatch.setattr(
        query_worker.importlib.util, "find_spec", lambda name: object() if managed_dependencies else None
    )
    monkeypatch.setitem(sys.modules, "pm.environments", SimpleNamespace(activate_dependencies=activated.append))
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setitem(sys.modules, "hermes_cli", SimpleNamespace(__file__=str(tmp_path / "hermes_cli/__init__.py")))
    monkeypatch.setitem(sys.modules, "agent.auxiliary_client", SimpleNamespace(call_llm=call))
    monkeypatch.setitem(
        sys.modules,
        "hermes_cli.config",
        SimpleNamespace(load_config=lambda: {"model": {"provider": "custom", "default": "configured-model"}}),
    )
    monkeypatch.setitem(sys.modules, "hermes_cli.runtime_provider", SimpleNamespace(resolve_runtime_provider=resolve))
    request = tmp_path / "request.txt"
    request.write_text("instruction", encoding="utf-8")
    paths = [str(tmp_path / "selected")] if host_paths else None
    monkeypatch.setattr(sys, "argv", ["-c", str(request), json.dumps(paths)])
    query_worker.main()
    assert sys.path[0] == (paths[0] if paths else str(tmp_path))
    assert activated == ([tmp_path] if managed_dependencies and not host_paths else [])


def test_extraction_and_retrieval_do_not_block_plugin_hook(tmp_path, monkeypatch):
    from memu.hosts.hermes import plugin

    entered, release, delivered = threading.Event(), threading.Event(), threading.Event()
    callbacks = {}
    calls = []

    def extract(prompt, **kwargs):
        entered.set()
        assert release.wait(5)
        return "selected topic"

    async def retrieve(query, *, query_kind):
        assert (query, query_kind) == ("selected topic", "extracted")
        calls.append("retrieve")
        return {"hits": [], "resources": []}

    def call(action, event):
        if action == "retrieve":
            return asyncio.run(hook.retrieve_context(tmp_path, {**event, "hermes_python": "host-python"}))
        calls.append(action)
        return {}

    def inject(message, *, session_key):
        assert session_key == "route-s"
        calls.append(message)
        delivered.set()
        return True

    monkeypatch.setattr(hermes, "_extract", extract)
    monkeypatch.setattr(hook, "retrieve", retrieve)
    monkeypatch.setattr(plugin, "_call", call)
    monkeypatch.setitem(sys.modules, "hermes_cli.plugin_session", SimpleNamespace(session_key=lambda: "route-s"))
    plugin.register(
        SimpleNamespace(register_hook=lambda name, callback: callbacks.update({name: callback}), inject_message=inject)
    )
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(callbacks["pre_llm_call"], user_message="x" * 2500, session_id="s")
        try:
            assert entered.wait(2)
            assert future.result(timeout=1) is None
            assert not delivered.is_set()
            callbacks["on_session_end"](session_id="s", completed=True)
            assert calls == []
        finally:
            release.set()
        assert delivered.wait(3)
    callbacks["pre_llm_call"](user_message=calls[-1], session_id="s")
    callbacks["on_session_end"](session_id="s", completed=True)
    assert calls[0] == "retrieve" and calls[-1] == "memorize"
