from __future__ import annotations

import json
import os
from typing import Any

import pytest

from memu import env as menv

typesafe_sdk = pytest.importorskip("typesafe_sdk", reason="install the 'jev' extra to test the official SDK contract")
httpx2 = pytest.importorskip("httpx2")

LIVE_API_KEY = menv.env("TYPESAFE_API_KEY")
RUN_LIVE = os.environ.get("MEMU_RUN_LIVE_JEV") == "1"

from memu.integrations.jev import (  # noqa: E402
    JevCandidate,
    JevRerankConfig,
    TypeSafeJevEvaluator,
)


async def test_official_sdk_sends_one_system_one_request() -> None:
    requests: list[Any] = []

    async def handler(request: Any) -> Any:
        requests.append(request)
        return httpx2.Response(
            200,
            json={
                "model": "jev-1.13.0",
                "answers": {
                    "segment_0": {"type": "noul", "noul": 0.94},
                    "resource_0": {"type": "noul", "noul": 0.08},
                },
                "usage": {"input_tokens": 77, "output_tokens": 2},
            },
        )

    client = typesafe_sdk.AsyncTypeSafeClient(
        api_key="test-key",
        transport=httpx2.MockTransport(handler),
    )
    evaluator = TypeSafeJevEvaluator(
        api_key="test-key",
        config=JevRerankConfig(model="jev-latest"),
        client=client,
    )

    result = await evaluator.evaluate(
        "How do I deploy?",
        [
            JevCandidate("segment_0", "segment", "Run make deploy", 0.8, 0),
            JevCandidate("resource_0", "resource", "Lunch menu", 0.7, 0),
        ],
    )
    await evaluator.aclose()

    assert len(requests) == 1
    assert requests[0].url.path == "/v1/systemone"
    payload = json.loads(requests[0].content)
    assert payload["model"] == "jev-latest"
    assert payload["state"] == {
        "query": "How do I deploy?",
        "candidates": {
            "segment_0": {"kind": "segment", "content": "Run make deploy"},
            "resource_0": {"kind": "resource", "content": "Lunch menu"},
        },
    }
    assert set(payload["questions"]) == {"segment_0", "resource_0"}
    for key, question in payload["questions"].items():
        assert question["type"] == "noul"
        assert key in question["instructions"]
        assert set(question["criteria"]) == {"true", "false"}

    assert result.model == "jev-1.13.0"
    assert result.scores == {"segment_0": 0.94, "resource_0": 0.08}
    assert result.input_tokens == 77
    assert result.output_tokens == 2
    assert result.latency_ms >= 0


@pytest.mark.integration
@pytest.mark.skipif(not (RUN_LIVE and LIVE_API_KEY), reason="set MEMU_RUN_LIVE_JEV=1 and TYPESAFE_API_KEY for live Jev")
async def test_live_jev_returns_probabilities_for_memory_candidates() -> None:
    assert LIVE_API_KEY is not None
    evaluator = TypeSafeJevEvaluator(
        api_key=LIVE_API_KEY,
        config=JevRerankConfig(model=menv.env("MEMU_JEV_MODEL", "jev-latest") or "jev-latest", timeout_seconds=10),
    )
    try:
        result = await evaluator.evaluate(
            "How do I deploy the service?",
            [
                JevCandidate("segment_0", "segment", "Run make deploy and verify the health endpoint.", 0.8, 0),
                JevCandidate("resource_0", "resource", "The office lunch menu changes every Friday.", 0.7, 0),
            ],
        )
    finally:
        await evaluator.aclose()

    assert result.model.startswith("jev")
    assert set(result.scores) == {"segment_0", "resource_0"}
    assert all(0 <= score <= 1 for score in result.scores.values())
    assert result.input_tokens is None or result.input_tokens > 0
