"""Vision-language model (VLM) clients for multimodal understanding.

Sibling package to :mod:`memu.llm`, scoped to the multimodal ``vision``
capability used by image/video preprocessing. It mirrors the LLM package layout:

- ``backends/``: per-provider vision request/response shapes (HTTP transport).
- ``http_client``/``openai_client``/``anthropic_client``: transport clients.
- ``gateway``: build a client from a :class:`memu.app.settings.VLMConfig`.
- ``defaults``: per-provider latest VLM model picks.
"""

from __future__ import annotations

from memu.vlm.base import VLMClient, encode_image
from memu.vlm.defaults import VLM_PROVIDER_DEFAULTS, default_vlm_model
from memu.vlm.gateway import build_vlm_client

__all__ = [
    "VLM_PROVIDER_DEFAULTS",
    "VLMClient",
    "build_vlm_client",
    "default_vlm_model",
    "encode_image",
]
