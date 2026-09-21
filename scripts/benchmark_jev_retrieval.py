#!/usr/bin/env python3
"""Measure warm memU + real Jev retrieval latency.

The first-stage embeddings are deterministic and local so the reported Jev
latency isolates the real TypeSafe request rather than another provider. Set
``TYPESAFE_API_KEY`` in the environment or ``~/.memu/config.env``; never pass a
credential on the command line.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
from datetime import UTC, datetime
from typing import Any

from memu import env as menv
from memu.app import MemoryService
from memu.integrations.jev import JevRerankConfig, JevRerankedMemoryBackend, TypeSafeJevEvaluator


class DeterministicEmbeddingClient:
    """Small local embedding fixture; Jev remains the only network model call."""

    embed_model = "benchmark-keywords-v1"

    async def embed(self, inputs: list[str]) -> tuple[list[list[float]], None]:
        return [self._vector(text) for text in inputs], None

    @staticmethod
    def _vector(text: str) -> list[float]:
        lowered = text.lower()
        return [
            float(any(word in lowered for word in ("deploy", "release", "health", "staging"))),
            float(any(word in lowered for word in ("lunch", "menu", "food"))),
            float(any(word in lowered for word in ("coffee", "preference", "profile"))),
            0.1,
        ]


def _percentile(samples: list[float], percentile: float) -> float:
    ordered = sorted(samples)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


async def _seed_service() -> MemoryService:
    service = MemoryService(database_config={"metadata_store": {"provider": "inmemory"}})
    embedding = DeterministicEmbeddingClient()
    service._embedding_pool._cache["default"] = embedding
    service._embedding_pool._cache["embedding"] = embedding
    await service.commit_results(
        recall_files=[
            {
                "name": "deployment",
                "track": "skill",
                "description": "production deployment procedure",
                "content": "Run make deploy.\nVerify the health endpoint.\nPromote the staging release.",
            },
            {
                "name": "lunch",
                "track": "memory",
                "description": "office lunch information",
                "content": "The lunch menu changes every Friday.",
            },
            {
                "name": "profile",
                "track": "memory",
                "description": "user preferences",
                "content": "The user prefers dark-roast coffee.",
            },
        ],
        resource=[
            {"path": "/workspace/DEPLOY.md", "description": "release and health-check runbook"},
            {"path": "/workspace/MENU.md", "description": "weekly office lunch menu"},
        ],
    )
    return service


async def benchmark(args: argparse.Namespace) -> dict[str, Any]:
    api_key = menv.env("TYPESAFE_API_KEY")
    if not api_key:
        message = "TYPESAFE_API_KEY is required in the environment or ~/.memu/config.env"
        raise SystemExit(message)

    base = await _seed_service()
    config = JevRerankConfig(
        model=args.model,
        min_relevance=args.min_relevance,
        timeout_seconds=args.timeout,
    )
    evaluator = TypeSafeJevEvaluator(api_key=api_key, config=config)
    reranked = JevRerankedMemoryBackend(base, config=config, evaluator=evaluator)
    query = "How do I deploy the service and verify it is healthy?"

    try:
        for _ in range(args.warmup):
            await reranked.progressive_retrieve(query)

        base_ms: list[float] = []
        total_ms: list[float] = []
        jev_ms: list[float] = []
        metadata: dict[str, Any] = {}
        for _ in range(args.runs):
            started = time.perf_counter()
            await base.progressive_retrieve(query)
            base_ms.append((time.perf_counter() - started) * 1000)

            started = time.perf_counter()
            result = await reranked.progressive_retrieve(query)
            total_ms.append((time.perf_counter() - started) * 1000)
            metadata = result["jev"]
            if not metadata.get("applied"):
                message = f"Jev was not applied: {metadata.get('error_type', metadata.get('reason'))}"
                raise RuntimeError(message)
            jev_ms.append(float(metadata["latency_ms"]))
    finally:
        await reranked.aclose()

    return {
        "measured_at": datetime.now(UTC).isoformat(),
        "region": os.environ.get("MEMU_BENCH_REGION", "unspecified"),
        "model": metadata.get("model", args.model),
        "runs": args.runs,
        "warmup_runs": args.warmup,
        "candidate_count": metadata.get("candidate_count"),
        "input_tokens_last_run": metadata.get("input_tokens"),
        "base_retrieval_ms": {
            "median": round(statistics.median(base_ms), 2),
            "p95": round(_percentile(base_ms, 0.95), 2),
        },
        "jev_provider_ms": {
            "median": round(statistics.median(jev_ms), 2),
            "p95": round(_percentile(jev_ms, 0.95), 2),
        },
        "total_retrieval_ms": {
            "median": round(statistics.median(total_ms), 2),
            "p95": round(_percentile(total_ms, 0.95), 2),
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--model", default=menv.env("MEMU_JEV_MODEL", "jev-latest"))
    parser.add_argument("--min-relevance", type=float, default=0.5)
    parser.add_argument("--timeout", type=float, default=10.0)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.runs < 1 or args.warmup < 0:
        message = "--runs must be positive and --warmup must not be negative"
        raise SystemExit(message)
    print(json.dumps(asyncio.run(benchmark(args)), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
