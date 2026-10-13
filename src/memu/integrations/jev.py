"""Opt-in TypeSafe Jev relevance filtering for memU retrieval results.

The core :class:`memu.app.MemoryService` remains embedding-only. This module
wraps its three-operation backend protocol and applies one System One request
after ordinary vector retrieval. Importing the module does not require the
optional TypeSafe SDK; only constructing the production evaluator does.
"""

from __future__ import annotations

import inspect
import math
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

from memu.agentic_backend import AgenticMemoryBackend

CandidateKind = Literal["segment", "resource"]
ErrorPolicy = Literal["fallback", "raise"]


class JevIntegrationError(RuntimeError):
    """Base error for Jev integration configuration and response failures."""


class JevDependencyError(JevIntegrationError):
    """The optional official TypeSafe SDK is not installed."""


class JevConfigurationError(JevIntegrationError):
    """Jev was enabled without a usable credential or configuration."""


class JevResponseError(JevIntegrationError):
    """Jev returned probabilities that do not cover the requested candidates."""


class JevRerankConfig(BaseModel):
    """Validated settings for one bounded Jev relevance request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model: str = Field(default="jev-latest", min_length=1)
    min_relevance: float = Field(default=0.5, ge=0.0, le=1.0)
    max_candidates: int = Field(default=32, ge=1, le=255)
    timeout_seconds: float = Field(default=1.5, gt=0.0, le=120.0)
    on_error: ErrorPolicy = "fallback"

    @field_validator("model")
    @classmethod
    def _model_must_not_be_blank(cls, value: str) -> str:
        model = value.strip()
        if not model:
            message = "model must not be blank"
            raise ValueError(message)
        return model


@dataclass(frozen=True, slots=True)
class JevCandidate:
    """The minimal candidate state sent to Jev."""

    key: str
    kind: CandidateKind
    text: str
    original_score: float
    position: int


@dataclass(frozen=True, slots=True)
class JevEvaluation:
    """Normalized output from one Jev System One request."""

    model: str
    scores: dict[str, float]
    latency_ms: int
    input_tokens: int | None
    output_tokens: int | None


class JevEvaluator(Protocol):
    """Small injectable seam around Jev inference."""

    async def evaluate(self, query: str, candidates: list[JevCandidate]) -> JevEvaluation: ...


class TypeSafeJevEvaluator:
    """Real Jev evaluator backed by TypeSafe's official asynchronous SDK."""

    def __init__(
        self,
        *,
        api_key: str,
        config: JevRerankConfig | Mapping[str, Any] | None = None,
        client: Any | None = None,
    ) -> None:
        self.config = _validate_config(config)
        if not api_key or not api_key.strip():
            message = "TYPESAFE_API_KEY must not be empty"
            raise JevConfigurationError(message)
        if client is None:
            try:
                from typesafe_sdk import AsyncTypeSafeClient, RetryPolicy
            except ImportError as exc:  # pragma: no cover - exact import failure is environment-specific
                message = 'Install the Jev integration with: pip install "memu-cli[jev]"'
                raise JevDependencyError(message) from exc
            client = AsyncTypeSafeClient(
                api_key=api_key,
                model=self.config.model,
                retry=RetryPolicy(max_retries=0),
                timeout=self.config.timeout_seconds,
            )
        self._client = client
        self._closed = False

    async def evaluate(self, query: str, candidates: list[JevCandidate]) -> JevEvaluation:
        if not candidates:
            message = "Jev evaluation requires at least one candidate"
            raise ValueError(message)

        state: dict[str, object] = {
            "query": query,
            "candidates": {
                candidate.key: {"kind": candidate.kind, "content": candidate.text} for candidate in candidates
            },
        }
        questions: dict[str, dict[str, object]] = {
            candidate.key: {
                "type": "noul",
                "instructions": (
                    f"Does candidate {candidate.key} contain concrete information directly useful "
                    "for answering the query in the state?"
                ),
                "criteria": {
                    "true": "The candidate directly helps answer the query with concrete information.",
                    "false": (
                        "The candidate is irrelevant, merely topically similar, or lacks information "
                        "useful for answering the query."
                    ),
                },
            }
            for candidate in candidates
        }

        started = time.perf_counter()
        response = await self._client.system_one(
            state=state,
            questions=questions,
            model=self.config.model,
            timeout=self.config.timeout_seconds,
        )
        latency_ms = round((time.perf_counter() - started) * 1000)
        scores = {key: float(answer.noul) for key, answer in response.nouls.items()}
        _validate_scores(candidates, scores)
        usage = response.usage
        return JevEvaluation(
            model=str(response.model),
            scores=scores,
            latency_ms=latency_ms,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        )

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        close = getattr(self._client, "aclose", None)
        if close is not None:
            result = close()
            if inspect.isawaitable(result):
                await result

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> None:
        await self.aclose()


class JevRerankedMemoryBackend:
    """Apply a single Jev relevance pass around any agentic memory backend."""

    def __init__(
        self,
        backend: AgenticMemoryBackend,
        *,
        config: JevRerankConfig | Mapping[str, Any] | None = None,
        evaluator: JevEvaluator | None = None,
        api_key: str | None = None,
    ) -> None:
        self.backend = backend
        self.config = _validate_config(config)
        self._evaluator = evaluator or TypeSafeJevEvaluator(api_key=api_key or "", config=self.config)
        self._closed = False

    async def list_all_recall_files(
        self,
        where: dict[str, Any] | None = None,
        *,
        cursor: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        return await self.backend.list_all_recall_files(where, cursor=cursor, limit=limit)

    async def commit_results(
        self,
        *,
        recall_files: list[dict[str, Any]] | None = None,
        resource: list[dict[str, Any]] | None = None,
        user: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self.backend.commit_results(recall_files=recall_files, resource=resource, user=user)

    async def progressive_retrieve(
        self,
        query: str,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        vector_result = await self.backend.progressive_retrieve(query, where=where)
        all_candidates = _collect_candidates(vector_result)
        candidates = all_candidates[: self.config.max_candidates]
        truncated_count = len(all_candidates) - len(candidates)
        if not candidates:
            return {
                **vector_result,
                "jev": {
                    "applied": False,
                    "fallback": False,
                    "provider": "typesafe",
                    "model": self.config.model,
                    "reason": "no_candidates",
                    "candidate_count": 0,
                    "retained_count": 0,
                    "min_relevance": self.config.min_relevance,
                    "truncated_count": 0,
                },
            }

        started = time.perf_counter()
        try:
            evaluation = await self._evaluator.evaluate(query, candidates)
            _validate_scores(candidates, evaluation.scores)
        except Exception as exc:
            if self.config.on_error == "raise":
                raise
            return {
                **vector_result,
                "jev": {
                    "applied": False,
                    "fallback": True,
                    "provider": "typesafe",
                    "model": self.config.model,
                    "latency_ms": round((time.perf_counter() - started) * 1000),
                    "error_type": type(exc).__name__,
                    "candidate_count": len(candidates),
                    "retained_count": len(all_candidates),
                    "min_relevance": self.config.min_relevance,
                    "truncated_count": truncated_count,
                },
            }

        retained = [
            candidate for candidate in candidates if evaluation.scores[candidate.key] >= self.config.min_relevance
        ]
        segments = _materialize_layer("segment", retained, evaluation.scores, vector_result.get("segments", []))
        resources = _materialize_layer("resource", retained, evaluation.scores, vector_result.get("resources", []))
        files = _roll_up_files(vector_result.get("files", []), segments)
        return {
            **vector_result,
            "segments": segments,
            "files": files,
            "resources": resources,
            "jev": {
                "applied": True,
                "fallback": False,
                "provider": "typesafe",
                "model": evaluation.model,
                "latency_ms": evaluation.latency_ms,
                "input_tokens": evaluation.input_tokens,
                "output_tokens": evaluation.output_tokens,
                "candidate_count": len(candidates),
                "retained_count": len(retained),
                "min_relevance": self.config.min_relevance,
                "truncated_count": truncated_count,
            },
        }

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        close = getattr(self._evaluator, "aclose", None)
        if close is not None:
            result = close()
            if inspect.isawaitable(result):
                await result

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> None:
        await self.aclose()


def _validate_config(config: JevRerankConfig | Mapping[str, Any] | None) -> JevRerankConfig:
    if isinstance(config, JevRerankConfig):
        return config
    return JevRerankConfig.model_validate(config or {})


def _collect_candidates(result: Mapping[str, Any]) -> list[JevCandidate]:
    candidates: list[JevCandidate] = []
    for position, item in enumerate(result.get("segments", [])):
        candidates.append(
            JevCandidate(
                key=f"segment_{position}",
                kind="segment",
                text=str(item.get("text") or ""),
                original_score=float(item.get("score", 0.0)),
                position=position,
            )
        )
    for position, item in enumerate(result.get("resources", [])):
        candidates.append(
            JevCandidate(
                key=f"resource_{position}",
                kind="resource",
                text=str(item.get("caption") or item.get("url") or ""),
                original_score=float(item.get("score", 0.0)),
                position=position,
            )
        )
    kind_order = {"segment": 0, "resource": 1}
    return sorted(
        candidates,
        key=lambda candidate: (-candidate.original_score, kind_order[candidate.kind], candidate.position),
    )


def _validate_scores(candidates: list[JevCandidate], scores: Mapping[str, float]) -> None:
    expected = {candidate.key for candidate in candidates}
    actual = set(scores)
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        message = f"Jev answer keys did not match candidates (missing={missing}, unexpected={unexpected})"
        raise JevResponseError(message)
    if any(not math.isfinite(score) or not 0.0 <= score <= 1.0 for score in scores.values()):
        message = "Jev relevance probabilities must be finite values from 0 to 1"
        raise JevResponseError(message)


def _materialize_layer(
    kind: CandidateKind,
    retained: list[JevCandidate],
    scores: Mapping[str, float],
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ranked: list[tuple[JevCandidate, dict[str, Any]]] = []
    for candidate in retained:
        if candidate.kind != kind:
            continue
        item = dict(items[candidate.position])
        item["jev_score"] = scores[candidate.key]
        ranked.append((candidate, item))
    ranked.sort(key=lambda pair: (-scores[pair[0].key], -pair[0].original_score, pair[0].position))
    return [item for _, item in ranked]


def _roll_up_files(files: list[dict[str, Any]], segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    file_scores: dict[Any, float] = {}
    for segment in segments:
        file_id = segment.get("recall_file_id")
        if file_id is None:
            continue
        score = float(segment["jev_score"])
        file_scores[file_id] = max(score, file_scores.get(file_id, -math.inf))

    ranked: list[dict[str, Any]] = []
    for item in files:
        file_id = item.get("id")
        if file_id not in file_scores:
            continue
        materialized = dict(item)
        materialized["jev_score"] = file_scores[file_id]
        ranked.append(materialized)
    ranked.sort(key=lambda item: (-float(item["jev_score"]), -float(item.get("score", 0.0))))
    return ranked


__all__ = [
    "JevCandidate",
    "JevConfigurationError",
    "JevDependencyError",
    "JevEvaluation",
    "JevEvaluator",
    "JevIntegrationError",
    "JevRerankConfig",
    "JevRerankedMemoryBackend",
    "JevResponseError",
    "TypeSafeJevEvaluator",
]
