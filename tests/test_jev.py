from __future__ import annotations

import asyncio
import builtins
import sys
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from memu import env as menv
from memu.app import MemoryService
from memu.cloud import CloudMemoryClient
from memu.integrations.jev import (
    JevCandidate,
    JevDependencyError,
    JevEvaluation,
    JevRerankConfig,
    JevRerankedMemoryBackend,
    TypeSafeJevEvaluator,
)


@pytest.fixture(autouse=True)
def _clear_memu_env_cache() -> Iterator[None]:
    """Keep config-file values from leaking beyond the test that loaded them."""
    menv.reload()
    yield
    menv.reload()


def _retrieval_result() -> dict[str, Any]:
    return {
        "segments": [
            {"id": "s1", "recall_file_id": "f1", "text": "topical only", "score": 0.90},
            {"id": "s2", "recall_file_id": "f2", "text": "direct answer", "score": 0.80},
            {"id": "s3", "recall_file_id": "f2", "text": "supporting detail", "score": 0.70},
        ],
        "files": [
            {"id": "f1", "name": "noise", "score": 0.90},
            {"id": "f2", "name": "answer", "score": 0.80},
        ],
        "resources": [
            {"id": "r1", "caption": "useful reference", "url": "/useful", "score": 0.85},
            {"id": "r2", "caption": "irrelevant reference", "url": "/noise", "score": 0.60},
        ],
    }


class StubBackend:
    def __init__(self, result: dict[str, Any] | None = None) -> None:
        self.result = result if result is not None else _retrieval_result()
        self.retrieve_calls: list[tuple[str, dict[str, Any] | None]] = []
        self.list_calls: list[tuple[dict[str, Any] | None, str | None, int]] = []
        self.commit_calls: list[dict[str, Any]] = []

    async def list_all_recall_files(
        self,
        where: dict[str, Any] | None = None,
        *,
        cursor: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        self.list_calls.append((where, cursor, limit))
        return {"recall_files": [{"name": "one"}], "next_cursor": None}

    async def progressive_retrieve(
        self,
        query: str,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.retrieve_calls.append((query, where))
        return deepcopy(self.result)

    async def commit_results(
        self,
        *,
        recall_files: list[dict[str, Any]] | None = None,
        resource: list[dict[str, Any]] | None = None,
        user: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        call = {"recall_files": recall_files, "resource": resource, "user": user}
        self.commit_calls.append(call)
        return call


class StubEvaluator:
    def __init__(
        self,
        scores: dict[str, float] | None = None,
        *,
        error: BaseException | None = None,
    ) -> None:
        self.scores = scores or {}
        self.error = error
        self.calls: list[tuple[str, list[JevCandidate]]] = []
        self.closed = False

    async def evaluate(self, query: str, candidates: list[JevCandidate]) -> JevEvaluation:
        self.calls.append((query, list(candidates)))
        if self.error is not None:
            raise self.error
        return JevEvaluation(
            model="jev-1.13.0",
            scores=dict(self.scores),
            latency_ms=87,
            input_tokens=123,
            output_tokens=5,
        )

    async def aclose(self) -> None:
        self.closed = True


async def test_wrapper_delegates_non_retrieval_operations() -> None:
    backend = StubBackend()
    evaluator = StubEvaluator()
    service = JevRerankedMemoryBackend(backend, evaluator=evaluator)

    listed = await service.list_all_recall_files({"user_id": "u1"}, cursor="next", limit=7)
    committed = await service.commit_results(
        recall_files=[{"name": "profile"}],
        resource=[{"path": "/notes"}],
        user={"user_id": "u1"},
    )

    assert listed == {"recall_files": [{"name": "one"}], "next_cursor": None}
    assert backend.list_calls == [({"user_id": "u1"}, "next", 7)]
    assert committed == {
        "recall_files": [{"name": "profile"}],
        "resource": [{"path": "/notes"}],
        "user": {"user_id": "u1"},
    }
    assert evaluator.calls == []


async def test_one_jev_call_filters_and_reranks_every_layer() -> None:
    backend = StubBackend()
    evaluator = StubEvaluator({
        "segment_0": 0.20,
        "segment_1": 0.95,
        "segment_2": 0.60,
        "resource_0": 0.70,
        "resource_1": 0.40,
    })
    service = JevRerankedMemoryBackend(
        backend,
        config=JevRerankConfig(min_relevance=0.5),
        evaluator=evaluator,
    )

    result = await service.progressive_retrieve("how do I deploy?", where={"user_id": "u1"})

    assert backend.retrieve_calls == [("how do I deploy?", {"user_id": "u1"})]
    assert len(evaluator.calls) == 1
    query, candidates = evaluator.calls[0]
    assert query == "how do I deploy?"
    # Candidates from both layers share one request and are merged by their
    # original vector score instead of starving the resource layer.
    assert [candidate.key for candidate in candidates] == [
        "segment_0",
        "resource_0",
        "segment_1",
        "segment_2",
        "resource_1",
    ]
    assert [(candidate.kind, candidate.text) for candidate in candidates] == [
        ("segment", "topical only"),
        ("resource", "useful reference"),
        ("segment", "direct answer"),
        ("segment", "supporting detail"),
        ("resource", "irrelevant reference"),
    ]

    assert [(item["id"], item["jev_score"]) for item in result["segments"]] == [
        ("s2", 0.95),
        ("s3", 0.60),
    ]
    assert [(item["id"], item["jev_score"]) for item in result["files"]] == [("f2", 0.95)]
    assert [(item["id"], item["jev_score"]) for item in result["resources"]] == [("r1", 0.70)]
    # Jev is additive: the original vector score remains inspectable.
    assert result["segments"][0]["score"] == 0.80
    assert result["jev"] == {
        "applied": True,
        "fallback": False,
        "provider": "typesafe",
        "model": "jev-1.13.0",
        "latency_ms": 87,
        "input_tokens": 123,
        "output_tokens": 5,
        "candidate_count": 5,
        "retained_count": 3,
        "min_relevance": 0.5,
        "truncated_count": 0,
    }


async def test_equal_jev_scores_use_vector_score_as_tiebreaker() -> None:
    backend = StubBackend({
        "segments": [
            {"id": "low", "recall_file_id": "f1", "text": "low", "score": 0.4},
            {"id": "high", "recall_file_id": "f2", "text": "high", "score": 0.9},
        ],
        "files": [{"id": "f1"}, {"id": "f2"}],
        "resources": [],
    })
    evaluator = StubEvaluator({"segment_0": 0.8, "segment_1": 0.8})
    service = JevRerankedMemoryBackend(backend, evaluator=evaluator)

    result = await service.progressive_retrieve("query")

    assert [item["id"] for item in result["segments"]] == ["high", "low"]


async def test_candidate_bound_keeps_best_cross_layer_scores_and_reports_truncation() -> None:
    evaluator = StubEvaluator({"segment_0": 0.8, "resource_0": 0.7})
    service = JevRerankedMemoryBackend(
        StubBackend(),
        config=JevRerankConfig(max_candidates=2),
        evaluator=evaluator,
    )

    result = await service.progressive_retrieve("query")

    assert [candidate.key for candidate in evaluator.calls[0][1]] == ["segment_0", "resource_0"]
    assert [item["id"] for item in result["segments"]] == ["s1"]
    assert [item["id"] for item in result["resources"]] == ["r1"]
    assert result["jev"]["candidate_count"] == 2
    assert result["jev"]["truncated_count"] == 3


async def test_empty_result_skips_jev() -> None:
    evaluator = StubEvaluator()
    service = JevRerankedMemoryBackend(
        StubBackend({"segments": [], "files": [], "resources": []}),
        evaluator=evaluator,
    )

    result = await service.progressive_retrieve("query")

    assert evaluator.calls == []
    assert result == {
        "segments": [],
        "files": [],
        "resources": [],
        "jev": {
            "applied": False,
            "fallback": False,
            "provider": "typesafe",
            "model": "jev-latest",
            "reason": "no_candidates",
            "candidate_count": 0,
            "retained_count": 0,
            "min_relevance": 0.5,
            "truncated_count": 0,
        },
    }


async def test_provider_error_falls_back_without_mutating_vector_layers() -> None:
    original = _retrieval_result()
    evaluator = StubEvaluator(error=RuntimeError("request body must not leak"))
    service = JevRerankedMemoryBackend(StubBackend(original), evaluator=evaluator)

    result = await service.progressive_retrieve("query")

    assert {key: result[key] for key in ("segments", "files", "resources")} == original
    assert result["jev"]["applied"] is False
    assert result["jev"]["fallback"] is True
    assert result["jev"]["error_type"] == "RuntimeError"
    assert result["jev"]["retained_count"] == 5
    assert "request body" not in str(result["jev"])


async def test_fallback_retains_candidates_beyond_the_jev_request_bound() -> None:
    service = JevRerankedMemoryBackend(
        StubBackend(),
        config=JevRerankConfig(max_candidates=2),
        evaluator=StubEvaluator(error=RuntimeError("down")),
    )

    result = await service.progressive_retrieve("query")

    assert len(result["segments"]) + len(result["resources"]) == 5
    assert result["jev"]["candidate_count"] == 2
    assert result["jev"]["retained_count"] == 5
    assert result["jev"]["truncated_count"] == 3


async def test_provider_error_can_be_strict() -> None:
    service = JevRerankedMemoryBackend(
        StubBackend(),
        config=JevRerankConfig(on_error="raise"),
        evaluator=StubEvaluator(error=RuntimeError("down")),
    )

    with pytest.raises(RuntimeError, match="down"):
        await service.progressive_retrieve("query")


async def test_cancellation_is_never_converted_to_fallback() -> None:
    service = JevRerankedMemoryBackend(
        StubBackend(),
        evaluator=StubEvaluator(error=asyncio.CancelledError()),
    )

    with pytest.raises(asyncio.CancelledError):
        await service.progressive_retrieve("query")


async def test_incomplete_evaluation_is_a_provider_error() -> None:
    service = JevRerankedMemoryBackend(
        StubBackend(),
        evaluator=StubEvaluator({"segment_0": 0.9}),
    )

    result = await service.progressive_retrieve("query")

    assert result["jev"]["fallback"] is True
    assert result["jev"]["error_type"] == "JevResponseError"


async def test_wrapper_closes_evaluator() -> None:
    evaluator = StubEvaluator()
    service = JevRerankedMemoryBackend(StubBackend(), evaluator=evaluator)

    async with service:
        pass

    assert evaluator.closed is True


async def test_real_memory_service_scopes_candidates_before_jev() -> None:
    class EmbeddingClient:
        embed_model = "scope-test"

        async def embed(self, inputs: list[str]) -> tuple[list[list[float]], None]:
            return [[1.0, 0.0] for _ in inputs], None

    service = MemoryService(database_config={"metadata_store": {"provider": "inmemory"}})
    embedding = EmbeddingClient()
    service._embedding_pool._cache["default"] = embedding
    service._embedding_pool._cache["embedding"] = embedding
    await service.commit_results(
        recall_files=[{"name": "private", "track": "memory", "description": "u1", "content": "u1-only memory"}],
        resource=[{"path": "/u1", "description": "u1-only resource"}],
        user={"user_id": "u1"},
    )
    await service.commit_results(
        recall_files=[{"name": "private", "track": "memory", "description": "u2", "content": "u2-secret memory"}],
        resource=[{"path": "/u2", "description": "u2-secret resource"}],
        user={"user_id": "u2"},
    )
    evaluator = StubEvaluator({"segment_0": 0.9, "resource_0": 0.8})
    reranked = JevRerankedMemoryBackend(service, evaluator=evaluator)

    result = await reranked.progressive_retrieve("private memory", where={"user_id": "u1"})

    sent_text = [candidate.text for candidate in evaluator.calls[0][1]]
    assert sent_text == ["u1-only memory", "u1-only resource"]
    assert all("u2-secret" not in text for text in sent_text)
    assert [segment["text"] for segment in result["segments"]] == ["u1-only memory"]
    assert [resource["caption"] for resource in result["resources"]] == ["u1-only resource"]


async def test_typesafe_evaluator_builds_one_batched_noul_request() -> None:
    class Client:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []
            self.closed = False

        async def system_one(self, **kwargs: Any) -> Any:
            self.calls.append(kwargs)
            return SimpleNamespace(
                model="jev-1.13.0",
                nouls={
                    "segment_0": SimpleNamespace(noul=0.91),
                    "resource_0": SimpleNamespace(noul=0.12),
                },
                usage=SimpleNamespace(input_tokens=42, output_tokens=2),
            )

        async def aclose(self) -> None:
            self.closed = True

    client = Client()
    evaluator = TypeSafeJevEvaluator(
        api_key="test-key",
        config=JevRerankConfig(model="jev-latest", timeout_seconds=2),
        client=client,
    )

    result = await evaluator.evaluate(
        "deploy?",
        [
            JevCandidate("segment_0", "segment", "run deploy", 0.9, 0),
            JevCandidate("resource_0", "resource", "lunch menu", 0.8, 0),
        ],
    )
    await evaluator.aclose()

    assert len(client.calls) == 1
    request = client.calls[0]
    assert request["model"] == "jev-latest"
    assert request["timeout"] == 2
    assert request["state"]["query"] == "deploy?"
    assert set(request["questions"]) == {"segment_0", "resource_0"}
    assert all(question["type"] == "noul" for question in request["questions"].values())
    assert result.scores == {"segment_0": 0.91, "resource_0": 0.12}
    assert result.input_tokens == 42
    assert client.closed is True


def test_typesafe_evaluator_disables_sdk_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    created: dict[str, Any] = {}

    class RetryPolicy:
        def __init__(self, *, max_retries: int) -> None:
            self.max_retries = max_retries

    class Client:
        def __init__(self, **kwargs: Any) -> None:
            created.update(kwargs)

    sdk = ModuleType("typesafe_sdk")
    sdk.AsyncTypeSafeClient = Client  # type: ignore[attr-defined]
    sdk.RetryPolicy = RetryPolicy  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "typesafe_sdk", sdk)

    TypeSafeJevEvaluator(api_key="test-key")

    assert created["api_key"] == "test-key"
    assert created["model"] == "jev-latest"
    assert created["timeout"] == 1.5
    assert created["retry"].max_retries == 0


def test_typesafe_evaluator_explains_missing_optional_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def import_without_sdk(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "typesafe_sdk":
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_sdk)

    with pytest.raises(JevDependencyError, match=r"memu-cli\[jev\]"):
        TypeSafeJevEvaluator(api_key="test-key")


def test_config_validates_bounds() -> None:
    with pytest.raises(ValueError):
        JevRerankConfig(min_relevance=1.01)
    with pytest.raises(ValueError):
        JevRerankConfig(max_candidates=0)
    with pytest.raises(ValueError):
        JevRerankConfig(timeout_seconds=0)


def test_backend_builder_is_unchanged_when_reranker_is_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMU_DB", ":memory:")
    monkeypatch.delenv("MEMU_RETRIEVAL_RERANKER", raising=False)
    menv.reload()

    backend = menv.build_agentic_memory_backend_from_env()

    assert type(backend) is MemoryService


def test_backend_builder_wraps_local_backend_when_jev_is_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMU_DB", ":memory:")
    monkeypatch.setenv("MEMU_RETRIEVAL_RERANKER", "jev")
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    menv.reload()
    evaluator = StubEvaluator()
    monkeypatch.setattr("memu.integrations.jev.TypeSafeJevEvaluator", lambda **_: evaluator)

    backend = menv.build_agentic_memory_backend_from_env()

    assert isinstance(backend, JevRerankedMemoryBackend)
    assert type(backend.backend) is MemoryService


def test_backend_builder_wraps_cloud_backend_when_jev_is_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMU_MEMORY_MODE", "cloud")
    monkeypatch.setenv("MEMU_CLOUD_API_KEY", "memu-key")
    monkeypatch.setenv("MEMU_RETRIEVAL_RERANKER", "jev")
    monkeypatch.setenv("TYPESAFE_API_KEY", "typesafe-key")
    menv.reload()
    evaluator = StubEvaluator()
    monkeypatch.setattr("memu.integrations.jev.TypeSafeJevEvaluator", lambda **_: evaluator)

    backend = menv.build_agentic_memory_backend_from_env()

    assert isinstance(backend, JevRerankedMemoryBackend)
    assert isinstance(backend.backend, CloudMemoryClient)


def test_backend_builder_rejects_unknown_reranker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMU_DB", ":memory:")
    monkeypatch.setenv("MEMU_RETRIEVAL_RERANKER", "mystery")
    menv.reload()

    with pytest.raises(menv.ConfigError, match="MEMU_RETRIEVAL_RERANKER"):
        menv.build_agentic_memory_backend_from_env()


def test_backend_builder_requires_typesafe_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMU_DB", ":memory:")
    monkeypatch.setenv("MEMU_RETRIEVAL_RERANKER", "jev")
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    menv.reload()

    with pytest.raises(menv.ConfigError, match="TYPESAFE_API_KEY"):
        menv.build_agentic_memory_backend_from_env()


def test_backend_builder_reads_typesafe_key_and_tuning_from_config_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.env"
    config_file.write_text(
        "\n".join([
            "MEMU_DB=:memory:",
            "MEMU_RETRIEVAL_RERANKER=jev",
            "TYPESAFE_API_KEY=file-key",
            "MEMU_JEV_MIN_RELEVANCE=0.7",
            "MEMU_JEV_MAX_CANDIDATES=9",
            "MEMU_JEV_ON_ERROR=raise",
        ]),
        encoding="utf-8",
    )
    monkeypatch.setenv("MEMU_CONFIG_ENV", str(config_file))
    for key in (
        "MEMU_DB",
        "MEMU_RETRIEVAL_RERANKER",
        "TYPESAFE_API_KEY",
        "MEMU_JEV_MIN_RELEVANCE",
        "MEMU_JEV_MAX_CANDIDATES",
        "MEMU_JEV_ON_ERROR",
    ):
        monkeypatch.delenv(key, raising=False)
    menv.reload()
    captured: dict[str, Any] = {}

    def evaluator_factory(**kwargs: Any) -> StubEvaluator:
        captured.update(kwargs)
        return StubEvaluator()

    monkeypatch.setattr("memu.integrations.jev.TypeSafeJevEvaluator", evaluator_factory)

    backend = menv.build_agentic_memory_backend_from_env()

    assert isinstance(backend, JevRerankedMemoryBackend)
    assert captured["api_key"] == "file-key"
    assert backend.config.min_relevance == 0.7
    assert backend.config.max_candidates == 9
    assert backend.config.on_error == "raise"


def test_backend_builder_rejects_invalid_jev_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMU_DB", ":memory:")
    monkeypatch.setenv("MEMU_RETRIEVAL_RERANKER", "jev")
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setenv("MEMU_JEV_MIN_RELEVANCE", "2")
    menv.reload()

    with pytest.raises(menv.ConfigError, match=r"MEMU_JEV_\*"):
        menv.build_agentic_memory_backend_from_env()
