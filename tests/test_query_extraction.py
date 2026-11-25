"""Shared extraction validation accepts useful output independently of length."""

import pytest

from memu import env
from memu.hosts.claude_code import query_extraction as claude
from memu.hosts.codex import query_extraction as codex
from memu.hosts.pi import query_extraction as pi
from memu.hosts.query_extraction import select_query, validate_query


@pytest.mark.parametrize("adapter", [codex, claude, pi])
@pytest.mark.parametrize("length", [0, 800, 801, 32001])
def test_extraction_disabled_by_default(adapter, length, monkeypatch):
    monkeypatch.delenv("MEMU_QUERY_EXTRACT_ENABLED", raising=False)
    monkeypatch.setattr(env, "_file_values", lambda: {})
    monkeypatch.setattr(adapter, "_extract", lambda *a, **kw: pytest.fail("Extraction must not run"))
    prompt = "中" * length
    trace = {}
    assert adapter.select_query(prompt, trace) == prompt[:800]
    assert trace["extraction_status"] == "disabled"
    assert trace["query_source"] == ("prefix" if length > 800 else "original")


@pytest.mark.parametrize("setting,expected", [("true", "topic"), ("false", "x" * 800)])
def test_extraction_uses_shared_config_file(setting, expected, monkeypatch):
    monkeypatch.delenv("MEMU_QUERY_EXTRACT_ENABLED", raising=False)
    monkeypatch.setattr(env, "_file_values", lambda: {"MEMU_QUERY_EXTRACT_ENABLED": setting})
    assert select_query("x" * 801, {}, lambda _: "topic") == expected


def test_environment_overrides_config_file(monkeypatch):
    monkeypatch.setenv("MEMU_QUERY_EXTRACT_ENABLED", "false")
    monkeypatch.setattr(env, "_file_values", lambda: {"MEMU_QUERY_EXTRACT_ENABLED": "true"})
    assert select_query("x" * 801, {}, lambda _: pytest.fail("Extraction must not run")) == "x" * 800


@pytest.mark.parametrize("query", ["Windows task cleanup", "中" * 201, "topic " * 400])
def test_extracted_query_is_retained_without_length_rejection(query, monkeypatch):
    monkeypatch.setenv("MEMU_QUERY_EXTRACT_ENABLED", "true")
    trace: dict[str, object] = {}
    selected = select_query("background " * 250, trace, lambda _: validate_query({"query": f"  {query}  "}))
    assert selected == query.strip()
    assert trace["query_source"] == "extracted"
    assert trace["extraction_status"] == "succeeded"


@pytest.mark.parametrize("value", [None, [], {}, {"query": None}, {"query": 3}, {"query": " \t\n"}])
def test_invalid_extracted_query_is_rejected(value):
    with pytest.raises(ValueError, match="Invalid extracted query"):
        validate_query(value)
