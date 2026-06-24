"""Tests for VLM (vision-language) wiring into image/video preprocessing.

Covers:
- ``vlm_config_from_llm`` derivation (provider/credentials reuse, model pick).
- Image/video preprocessors using the VLM client (not the chat LLM client).
- ``MemoryService`` routing vision modalities to the VLM client and text
  modalities to the chat LLM client.
"""

from __future__ import annotations

import asyncio
from typing import Any

from memu.app.service import MemoryService
from memu.app.settings import LLMConfig, vlm_config_from_llm
from memu.preprocess import preprocess_resource
from memu.preprocess.base import PreprocessContext


class _RecordingVisionClient:
    """Vision client that records calls and returns a tagged response."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.vision_calls: list[str] = []

    async def vision(self, prompt: str, image_path: str, *, system_prompt: str | None = None, **_: Any) -> str:
        self.vision_calls.append(image_path)
        return "<detailed_description>a cat</detailed_description><caption>cat</caption>"


def _make_ctx(*, llm_client: Any, vlm_client: Any) -> PreprocessContext:
    return PreprocessContext(
        get_llm_client=lambda: llm_client,
        get_vlm_client=lambda: vlm_client,
        escape_prompt_value=lambda s: s,
        extract_json_blob=lambda s: s,
        resolve_custom_prompt=lambda _p, _v: "",
        multimodal_preprocess_prompts={},
    )


def test_vlm_config_from_llm_openai_sdk() -> None:
    cfg = vlm_config_from_llm(LLMConfig())
    assert cfg.provider == "openai"
    assert cfg.client_backend == "sdk"
    assert cfg.vlm_model == "gpt-5.4"


def test_vlm_config_from_llm_claude_http_reuses_credentials() -> None:
    llm = LLMConfig(provider="claude", client_backend="httpx", api_key="secret")
    cfg = vlm_config_from_llm(llm)
    assert cfg.provider == "claude"
    assert cfg.client_backend == "httpx"
    assert cfg.api_key == "secret"
    assert cfg.base_url == llm.base_url
    assert cfg.vlm_model == "claude-sonnet-4-6"


def test_vlm_config_from_llm_anthropic_backend_maps_provider() -> None:
    # The anthropic SDK backend leaves provider generic; it must still resolve a
    # Claude VLM model rather than the OpenAI default.
    cfg = vlm_config_from_llm(LLMConfig(client_backend="anthropic"))
    assert cfg.provider == "claude"
    assert cfg.vlm_model == "claude-sonnet-4-6"


def test_vlm_config_unknown_provider_falls_back_to_chat_model() -> None:
    # DeepSeek has no first-party VLM; fall back to the configured chat model.
    llm = LLMConfig(provider="deepseek", client_backend="httpx")
    cfg = vlm_config_from_llm(llm)
    assert cfg.vlm_model == llm.chat_model


def test_image_preprocess_uses_vlm_client() -> None:
    llm = _RecordingVisionClient("llm")
    vlm = _RecordingVisionClient("vlm")
    ctx = _make_ctx(llm_client=llm, vlm_client=vlm)
    image_path = "/workspace/x.png"

    result = asyncio.run(preprocess_resource(modality="image", local_path=image_path, text=None, ctx=ctx))

    assert vlm.vision_calls == [image_path]
    assert llm.vision_calls == []
    assert result[0]["text"] == "a cat"


def test_service_routes_vision_modalities_to_vlm(monkeypatch: Any) -> None:
    svc = MemoryService()
    captured: dict[str, Any] = {}

    async def _fake_preprocess(*, local_path: str, text: str | None, modality: str, llm_client: Any) -> list:
        captured["client"] = llm_client
        return []

    monkeypatch.setattr(svc, "_preprocess_resource_url", _fake_preprocess)
    monkeypatch.setattr(svc, "_get_vlm_client", lambda *a, **k: "VLM_CLIENT")
    monkeypatch.setattr(svc, "_get_step_llm_client", lambda *a, **k: "CHAT_CLIENT")
    resource_path = "/workspace/x"

    async def _run(modality: str) -> Any:
        state = {"local_path": resource_path, "raw_text": None, "modality": modality}
        await svc._memorize_preprocess_multimodal(state, {})
        return captured["client"]

    assert asyncio.run(_run("image")) == "VLM_CLIENT"
    assert asyncio.run(_run("video")) == "VLM_CLIENT"
    assert asyncio.run(_run("document")) == "CHAT_CLIENT"
    assert asyncio.run(_run("conversation")) == "CHAT_CLIENT"


def test_service_falls_back_to_chat_client_when_vlm_profile_missing(monkeypatch: Any) -> None:
    svc = MemoryService()
    captured: dict[str, Any] = {}

    async def _fake_preprocess(*, local_path: str, text: str | None, modality: str, llm_client: Any) -> list:
        captured["client"] = llm_client
        return []

    monkeypatch.setattr(svc, "_preprocess_resource_url", _fake_preprocess)
    monkeypatch.setattr(svc, "_get_vlm_client", lambda *a, **k: (_ for _ in ()).throw(KeyError("missing profile")))
    monkeypatch.setattr(svc, "_get_step_llm_client", lambda *a, **k: "CHAT_CLIENT")

    state = {"local_path": "/workspace/x", "raw_text": None, "modality": "image"}
    asyncio.run(svc._memorize_preprocess_multimodal(state, {}))

    assert captured["client"] == "CHAT_CLIENT"
