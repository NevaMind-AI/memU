from __future__ import annotations

import ast
import json
from pathlib import Path

from memu.llm.wrapper import _extract_usage_from_raw_response

ROOT = Path(__file__).resolve().parents[1]


def test_llm_usage_aggregates_batched_embedding_raw_responses() -> None:
    raw_responses = [
        {
            "usage": {
                "prompt_tokens": 3,
                "total_tokens": 3,
                "prompt_tokens_details": {"cached_tokens": 1},
            }
        },
        {
            "usage": {
                "prompt_tokens": 5,
                "total_tokens": 5,
                "prompt_tokens_details": {"cached_tokens": 2},
            }
        },
    ]

    usage = _extract_usage_from_raw_response(kind="embed", raw_response=raw_responses)

    assert usage["input_tokens"] == 8
    assert usage["total_tokens"] == 8
    assert usage["cached_input_tokens"] == 3
    json.dumps(usage)


def test_openai_sdk_batched_embed_returns_all_raw_responses_for_usage() -> None:
    source = (ROOT / "src/memu/llm/openai_sdk.py").read_text(encoding="utf-8")
    function_source = _function_source(source, "embed")

    assert "raw_responses.append(response)" in function_source
    assert "return all_embeddings, raw_responses" in function_source
    assert "last_response" not in function_source


def _function_source(source: str, name: str) -> str:
    module = ast.parse(source)
    for node in ast.walk(module):
        if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef) and node.name == name:
            segment = ast.get_source_segment(source, node)
            assert segment is not None
            return segment
    raise AssertionError(f"function {name!r} not found")
