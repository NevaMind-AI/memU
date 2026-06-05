#!/usr/bin/env python3
"""
Opt-in LazyLLM integration smoke test.

Usage:
    export MEMU_QWEN_API_KEY=your_api_key
    export MEMU_RUN_LAZYLLM_TESTS=1
    uv run python -m pytest tests/test_lazyllm.py

Manual run:
    export MEMU_QWEN_API_KEY=your_api_key
    python tests/test_lazyllm.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_LAZYLLM_TESTS_ENV = "MEMU_RUN_LAZYLLM_TESTS"

# Add src to sys.path before importing memu from a source checkout.
src_path = str(PROJECT_ROOT / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from memu.llm.lazyllm_client import LazyLLMClient  # noqa: E402


async def run_lazyllm_workflow() -> bool:
    """Run the LazyLLM-backed chat/embed/vision smoke workflow."""
    if not os.environ.get("MEMU_QWEN_API_KEY"):
        msg = "MEMU_QWEN_API_KEY is required for the LazyLLM integration workflow"
        raise RuntimeError(msg)

    print("LazyLLM Backend Test")
    print("=" * 60)

    try:
        client = LazyLLMClient(
            llm_source="qwen",
            vlm_source="qwen",
            embed_source="qwen",
            stt_source="qwen",
            chat_model="qwen-plus",
            vlm_model="qwen-vl-plus",
            embed_model="text-embedding-v3",
            stt_model="qwen-audio-turbo",
        )
        print("[OK] LazyLLMClient initialized successfully")
    except Exception as exc:
        print(f"[ERROR] Failed to initialize LazyLLMClient: {exc}")
        return False

    print("\n[Test 1] Testing chat...")
    try:
        test_text = (
            "Python is widely used for data analysis, machine learning, and web services. "
            "Summarize this short technical note in one sentence."
        )
        result = await client.chat(test_text)
        print("[OK] Chat successful")
        print(f"  Result: {result[:100]}...")
    except Exception as exc:
        print(f"[ERROR] Chat failed: {exc}")
        return False

    print("\n[Test 2] Testing embedding...")
    try:
        test_texts = ["Hello world", "How are you", "Nice to meet you"]
        embeddings = await client.embed(test_texts)
        print("[OK] Embedding successful")
        print(f"  Generated {len(embeddings)} embeddings")
        if embeddings and embeddings[0]:
            print(f"  Embedding dimension: {len(embeddings[0])}")
    except Exception as exc:
        print(f"[ERROR] Embedding failed: {exc}")
        return False

    print("\n[Test 3] Testing vision...")
    test_image_path = PROJECT_ROOT / "examples" / "resources" / "images" / "image1.png"
    if test_image_path.exists():
        try:
            result, _ = await client.vision(prompt="Describe the image content.", image_path=str(test_image_path))
            print("[OK] Vision successful")
            print(f"  Result: {result[:100]}...")
        except Exception as exc:
            print(f"[ERROR] Vision failed: {exc}")
            return False
    else:
        print(f"[WARN] Skipped vision check: test image not found at {test_image_path}")

    return True


async def test_lazyllm_client() -> None:
    """Opt-in pytest integration check for LazyLLM-backed model calls."""
    import pytest

    if os.environ.get(RUN_LAZYLLM_TESTS_ENV) != "1":
        pytest.skip(f"Set {RUN_LAZYLLM_TESTS_ENV}=1 to run the LazyLLM integration workflow")
    if not os.environ.get("MEMU_QWEN_API_KEY"):
        pytest.skip("MEMU_QWEN_API_KEY is required for the LazyLLM integration workflow")

    assert await run_lazyllm_workflow()


def main() -> int:
    return 0 if asyncio.run(run_lazyllm_workflow()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
