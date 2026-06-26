"""
Example 6: Multimodal Preprocessing -> Extracted Text + Caption

This example exercises memU's preprocessing stage for every supported modality
(conversation, document, image, audio, video) and prints what each preprocessor
extracts. It is a quick way to verify that multimodal extraction works end to end
against a real provider:

- conversation / document : chat LLM (text understanding)
- image / video           : VLM vision (video uses a sampled mid-frame)
- audio                   : speech-to-text transcription + chat LLM cleanup

Requirements:
- An OpenAI API key with access to a chat model, a vision model, and the
  transcription model (``gpt-4o-mini-transcribe``).
- ``ffmpeg``/``ffprobe`` on PATH for the video frame extraction.
- Optional document extras for PDF/Office input: ``pip install 'memu-py[document]'``.

Usage:
    export OPENAI_API_KEY=your_api_key
    # Optional model overrides (defaults to the library defaults):
    #   export MEMU_CHAT_MODEL=gpt-4o-mini
    #   export MEMU_VLM_MODEL=gpt-4o-mini
    python examples/example_6_preprocess_modalities.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from memu.app import MemoryService

# Allow running from a source checkout without installing the package.
sys.path.insert(0, os.path.abspath("src"))

RESOURCES = "examples/resources"

# (modality, file). Vision modalities are routed to the VLM client automatically.
CASES: list[tuple[str, str]] = [
    ("conversation", f"{RESOURCES}/conversations/conv1.json"),
    ("document", f"{RESOURCES}/docs/doc1.txt"),
    ("document", f"{RESOURCES}/docs/doc_sample.pdf"),
    ("image", f"{RESOURCES}/images/image1.png"),
    ("audio", f"{RESOURCES}/audio/audio_intro.mp3"),
    ("video", f"{RESOURCES}/video/video_test.mp4"),
]

VISION_MODALITIES = {"image", "video"}


def build_service() -> MemoryService:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        msg = "Please set OPENAI_API_KEY environment variable"
        raise ValueError(msg)

    default_profile: dict[str, str] = {"api_key": api_key}
    chat_model = os.getenv("MEMU_CHAT_MODEL")
    if chat_model:
        default_profile["chat_model"] = chat_model

    service = MemoryService(llm_profiles={"default": default_profile})

    # VLM profiles are derived from the LLM profile; allow an explicit override of
    # the vision model (handy when a default vision model is unavailable).
    vlm_model = os.getenv("MEMU_VLM_MODEL")
    if vlm_model:
        for cfg in service.vlm_profiles.values():
            cfg.vlm_model = vlm_model

    return service


def _preview(value: str | None, limit: int = 500) -> str:
    if not value:
        return "<empty>"
    value = value.strip()
    return value if len(value) <= limit else value[:limit] + f"... [+{len(value) - limit} chars]"


async def preprocess_one(service: MemoryService, modality: str, path: str) -> bool:
    """Run the preprocessing stage for a single resource and print the result."""
    print("\n" + "=" * 72)
    print(f"MODALITY: {modality}  ({os.path.basename(path)})")
    print("-" * 72)

    if not os.path.exists(path):
        print(f"  SKIP: missing sample file {path}")
        return False

    # Ingest (copies the file into the resources dir and extracts inline text for
    # text modalities), then run the modality-specific preprocessor. Vision
    # modalities use the VLM client; everything else uses the chat LLM client.
    local_path, raw_text = await service.fs.fetch(path, modality)
    if modality in VISION_MODALITIES:
        client = service._get_vlm_client(service.memorize_config.vlm_profile)
    else:
        client = service._get_llm_client("default")

    segments = await service._preprocess_resource_url(
        local_path=local_path,
        text=raw_text,
        modality=modality,
        llm_client=client,
    )

    extracted = False
    for i, seg in enumerate(segments):
        print(f"  [segment {i}] caption: {_preview(seg.get('caption'), 200)}")
        print(f"  [segment {i}] text   : {_preview(seg.get('text'))}")
        if seg.get("text"):
            extracted = True
    return extracted


async def main() -> None:
    print("Example 6: Multimodal Preprocessing")
    print("-" * 50)

    service = build_service()
    results: list[tuple[str, str, bool]] = []
    for modality, path in CASES:
        try:
            ok = await preprocess_one(service, modality, path)
        except Exception as e:
            print(f"  ERROR: {e}")
            ok = False
        results.append((modality, os.path.basename(path), ok))

    print("\n" + "#" * 72)
    print("SUMMARY")
    print("#" * 72)
    for modality, name, ok in results:
        print(f"  [{'OK  ' if ok else 'FAIL'}] {modality:<12} {name}")


if __name__ == "__main__":
    asyncio.run(main())
