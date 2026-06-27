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
from memu.vlm.backends.openrouter import OpenRouterVLMBackend
from memu.vlm.http_client import HTTPVLMClient


class _RecordingVisionClient:
    """Vision client that records calls and returns a tagged response."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.vision_calls: list[str] = []

    async def vision(self, prompt: str, image_path: str, *, system_prompt: str | None = None, **_: Any) -> str:
        self.vision_calls.append(image_path)
        return "<detailed_description>a cat</detailed_description><caption>cat</caption>"


class _RecordingVideoClient:
    """VLM client with native video support that records image/video calls."""

    supports_video = True

    def __init__(self) -> None:
        self.video_calls: list[str] = []
        self.vision_calls: list[str] = []

    async def video(self, prompt: str, video_path: str, *, system_prompt: str | None = None, **_: Any) -> str:
        self.video_calls.append(video_path)
        return "<detailed_description>a dog playing fetch</detailed_description><caption>dog playing</caption>"

    async def vision(self, prompt: str, image_path: str, *, system_prompt: str | None = None, **_: Any) -> str:
        self.vision_calls.append(image_path)
        return "<detailed_description>a frame</detailed_description><caption>frame</caption>"


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


def test_vlm_config_from_llm_openrouter_uses_video_capable_model() -> None:
    # An OpenRouter LLM profile (httpx transport) derives a VLM config that keeps
    # the httpx backend and defaults to a video-capable model so native
    # whole-video understanding works out of the box.
    cfg = vlm_config_from_llm(LLMConfig(provider="openrouter", client_backend="httpx"))
    assert cfg.provider == "openrouter"
    assert cfg.client_backend == "httpx"
    assert cfg.vlm_model == "minimax/minimax-m3"


def test_openrouter_backend_supports_native_video() -> None:
    backend = OpenRouterVLMBackend()
    assert backend.supports_video is True

    payload = backend.build_video_payload(
        prompt="Describe this video.",
        video_data_uri="data:video/mp4;base64,QUJD",
        system_prompt=None,
        vlm_model="minimax/minimax-m3",
        max_tokens=None,
    )
    content = payload["messages"][0]["content"]
    video_part = next(part for part in content if part["type"] == "video_url")
    assert video_part["video_url"]["url"] == "data:video/mp4;base64,QUJD"


def test_http_vlm_client_exposes_backend_video_capability() -> None:
    # OpenRouter advertises native video; plain OpenAI-compatible does not.
    openrouter = HTTPVLMClient(
        base_url="https://openrouter.ai", api_key="k", vlm_model="minimax/minimax-m3", provider="openrouter"
    )
    assert openrouter.supports_video is True

    openai = HTTPVLMClient(
        base_url="https://api.openai.com/v1", api_key="k", vlm_model="gpt-5.4", provider="openai"
    )
    assert openai.supports_video is False


def test_video_uses_native_video_when_supported() -> None:
    # A video-capable client analyzes the whole video file directly; no frame
    # extraction / image vision call happens.
    client = _RecordingVideoClient()
    ctx = _make_ctx(llm_client=client, vlm_client=client)
    video_path = "/workspace/clip.mp4"

    result = asyncio.run(
        preprocess_resource(modality="video", local_path=video_path, text=None, ctx=ctx, llm_client=client)
    )

    assert client.video_calls == [video_path]
    assert client.vision_calls == []
    assert result[0]["text"] == "a dog playing fetch"
    assert result[0]["caption"] == "dog playing"


def test_video_without_native_support_skips_no_frame_fallback() -> None:
    # A client without native video support must NOT degrade to middle-frame image
    # analysis: the video is skipped (no description) and vision() is never called.
    client = _RecordingVisionClient("vlm")
    ctx = _make_ctx(llm_client=client, vlm_client=client)

    result = asyncio.run(
        preprocess_resource(modality="video", local_path="/workspace/clip.mp4", text=None, ctx=ctx, llm_client=client)
    )

    assert client.vision_calls == []
    assert result[0]["text"] is None
    assert result[0]["caption"] is None
