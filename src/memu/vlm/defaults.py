"""Per-provider default VLM (vision-language) models.

Maps a provider identifier to its latest vision-capable (flagship multimodal)
model. Used by :class:`memu.app.settings.VLMConfig` to pick a strong default for
image/video understanding instead of the small/fast chat default in
``memu.app.settings._PROVIDER_DEFAULTS``. Verified June 2026.
"""

from __future__ import annotations

# Only providers whose first-party API offers native vision (image) understanding
# are listed. Text-only providers (e.g. DeepSeek's V4 API) are intentionally
# excluded. Verified via provider docs, June 2026.
VLM_PROVIDER_DEFAULTS: dict[str, str] = {
    "openai": "gpt-5.4",
    "grok": "grok-4-1",
    "claude": "claude-sonnet-4-6",
    "minimax": "MiniMax-M3",
    "kimi": "kimi-k2.6",
    "doubao": "doubao-seed-2.0-pro",
    # OpenRouter natively understands whole videos via its ``video_url`` content
    # type. MiniMax-M3 handles both images and video, tracks temporal changes
    # across frames, and is region-available (unlike Google/Gemini on OpenRouter).
    "openrouter": "minimax/minimax-m3",
}


def default_vlm_model(provider: str) -> str | None:
    """Return the default latest VLM model for ``provider`` (``None`` if unknown)."""
    return VLM_PROVIDER_DEFAULTS.get(provider.lower())
