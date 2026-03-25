"""Tests for reasoning_content fallback in content extraction helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from memu.llm.backends.base import _extract_content_from_dict
from memu.llm.openai_sdk import _extract_content


# -- _extract_content (SDK path, ChatCompletion objects) --


def _fake_completion(content=None, reasoning_content=None):
    """Build a minimal ChatCompletion-like object."""
    msg = MagicMock()
    msg.content = content
    # reasoning_content is an extra attr on some providers
    if reasoning_content is not None:
        msg.reasoning_content = reasoning_content
    else:
        # simulate the attr not existing at all
        del msg.reasoning_content
    choice = SimpleNamespace(message=msg)
    return SimpleNamespace(choices=[choice])


class TestExtractContent:
    def test_normal_content(self):
        resp = _fake_completion(content="hello world")
        assert _extract_content(resp) == "hello world"

    def test_reasoning_content_fallback(self):
        resp = _fake_completion(content=None, reasoning_content="thought result")
        assert _extract_content(resp) == "thought result"

    def test_empty_string_content_falls_back(self):
        resp = _fake_completion(content="", reasoning_content="fallback")
        assert _extract_content(resp) == "fallback"

    def test_both_none_returns_empty(self):
        resp = _fake_completion(content=None)
        assert _extract_content(resp) == ""

    def test_content_preferred_over_reasoning(self):
        resp = _fake_completion(content="real answer", reasoning_content="thinking")
        assert _extract_content(resp) == "real answer"


# -- _extract_content_from_dict (HTTP path, raw dicts) --


def _fake_dict_response(content=None, reasoning_content=None):
    """Build a minimal raw API response dict."""
    msg = {}
    if content is not None:
        msg["content"] = content
    if reasoning_content is not None:
        msg["reasoning_content"] = reasoning_content
    return {"choices": [{"message": msg}]}


class TestExtractContentFromDict:
    def test_normal_content(self):
        data = _fake_dict_response(content="hello")
        assert _extract_content_from_dict(data) == "hello"

    def test_reasoning_content_fallback(self):
        data = _fake_dict_response(reasoning_content="thought")
        assert _extract_content_from_dict(data) == "thought"

    def test_empty_string_content_falls_back(self):
        data = _fake_dict_response(content="", reasoning_content="fb")
        assert _extract_content_from_dict(data) == "fb"

    def test_both_missing_returns_empty(self):
        data = _fake_dict_response()
        assert _extract_content_from_dict(data) == ""

    def test_content_preferred_over_reasoning(self):
        data = _fake_dict_response(content="answer", reasoning_content="thinking")
        assert _extract_content_from_dict(data) == "answer"

    def test_none_content_with_reasoning(self):
        data = _fake_dict_response(content=None, reasoning_content="result")
        assert _extract_content_from_dict(data) == "result"
