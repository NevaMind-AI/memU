"""Span + metric + log lifecycle for a single memU memory operation.

The three signals are emitted together so they always agree: a
:func:`memory_operation` block opens the ``memory.*`` span, times the body into
``memory_operation_duration_seconds``, and writes one correlated OTel log record
(trace/span id attached by the SDK logging bridge) when the block ends —
whether it succeeds or raises.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode

from memu.observability import instruments, providers, semconv

_TRACER_SCOPE = "memu.observability"
_LOG = logging.getLogger("memu.observability")


def _tracer() -> trace.Tracer:
    return providers.get_tracer(_TRACER_SCOPE, semconv.SEMCONV_VERSION)


class OperationScope:
    """Handle a caller uses to attach result attributes to the live operation.

    Every attribute is mirrored onto both the span and the operation's log
    record, so a backend that only ingests one of the two still sees the same
    facts. ``None`` values are dropped (an absent optional attribute per spec).
    """

    def __init__(self, span: trace.Span, operation: str, store_kind: str) -> None:
        self.span = span
        self.operation = operation
        self.store_kind = store_kind
        self._log_attrs: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        if value is None:
            return
        self.span.set_attribute(key, value)
        self._log_attrs[key] = value


@contextmanager
def memory_operation(
    span_name: str,
    operation: str,
    store_kind: str,
    *,
    tenant: str | None = None,
) -> Iterator[OperationScope]:
    """Trace, time, and log one memory operation.

    ``span_name``/``operation`` come from :mod:`memu.observability.semconv`
    (e.g. ``SPAN_MEMORY_READ`` / ``OP_SEARCH``). ``store_kind`` is the backend
    label shared by the span and every metric this op records.
    """
    start = time.perf_counter()
    with _tracer().start_as_current_span(span_name, kind=SpanKind.INTERNAL) as span:
        span.set_attribute(semconv.ATTR_OPERATION, operation)
        span.set_attribute(semconv.ATTR_STORE_KIND, store_kind)
        span.set_attribute(semconv.ATTR_SUT_NAME, semconv.SUT_NAME)
        scope = OperationScope(span, operation, store_kind)
        if tenant:
            scope.set(semconv.ATTR_TENANT, tenant)
        try:
            yield scope
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
            duration = time.perf_counter() - start
            instruments.record_operation_duration(operation, store_kind, duration)
            _emit_log(scope, duration, error=exc)
            raise
        duration = time.perf_counter() - start
        span.set_status(Status(StatusCode.OK))
        instruments.record_operation_duration(operation, store_kind, duration)
        _emit_log(scope, duration, error=None)


def _emit_log(scope: OperationScope, duration: float, *, error: BaseException | None) -> None:
    attrs: dict[str, Any] = {
        semconv.ATTR_OPERATION: scope.operation,
        semconv.ATTR_STORE_KIND: scope.store_kind,
        semconv.ATTR_SUT_NAME: semconv.SUT_NAME,
        "memory.duration_s": round(duration, 6),
        **scope._log_attrs,
    }
    if error is None:
        _LOG.info("memory.%s ok", scope.operation, extra=attrs)
    else:
        attrs["memory.error"] = type(error).__name__
        _LOG.error("memory.%s failed", scope.operation, extra=attrs)


async def traced_embed(embed_client: Any, texts: list[str]) -> tuple[list[list[float]], Any]:
    """Wrap ``EmbeddingClient.embed`` in a ``memory.embed`` child span.

    Records the embedder model and — when the provider returns token usage —
    the ``memory.embed.token_count`` attribute and the
    ``memory_embed_token_total`` counter. Returns the client's ``(vectors,
    raw_response)`` tuple unchanged.
    """
    model = getattr(embed_client, "embed_model", "unknown")
    with _tracer().start_as_current_span(semconv.SPAN_MEMORY_EMBED, kind=SpanKind.INTERNAL) as span:
        span.set_attribute(semconv.ATTR_EMBEDDER_MODEL, model)
        span.set_attribute(semconv.ATTR_SUT_NAME, semconv.SUT_NAME)
        vectors, raw = await embed_client.embed(texts)
        tokens = _extract_tokens(raw)
        if tokens:
            span.set_attribute(semconv.ATTR_EMBED_TOKEN_COUNT, tokens)
            instruments.record_embed_tokens(model, tokens)
        return vectors, raw


def _extract_tokens(raw: Any) -> int:
    """Best-effort token count from an embedding provider's raw response.

    Handles the OpenAI SDK object (``raw.usage.total_tokens``) and the raw-HTTP
    dict shape (``raw["usage"]["total_tokens"]``); anything else yields 0.
    """
    if raw is None:
        return 0
    usage = getattr(raw, "usage", None)
    if usage is None and isinstance(raw, Mapping):
        usage = raw.get("usage")
    if usage is None:
        return 0
    for key in ("total_tokens", "prompt_tokens"):
        value = getattr(usage, key, None)
        if value is None and isinstance(usage, Mapping):
            value = usage.get(key)
        if isinstance(value, int) and value > 0:
            return value
    return 0


@dataclass(frozen=True)
class StoreSnapshot:
    """A point-in-time count of what a store holds, split by tier."""

    files: int
    segments: int
    resources: int
    content_bytes: int

    @property
    def items(self) -> int:
        """Logical memory items = recall files + resources (segments are vectors)."""
        return self.files + self.resources


def snapshot_store(store: Any) -> StoreSnapshot:
    """Count files / segments / resources and their content bytes in ``store``."""
    files = store.recall_file_repo.list_recall_files()
    resources = store.resource_repo.list_resources()
    segments = store.recall_file_segment_repo.list_segments()
    content_bytes = sum(len((f.content or "").encode("utf-8")) for f in files.values())
    content_bytes += sum(len((r.caption or "").encode("utf-8")) for r in resources.values())
    return StoreSnapshot(
        files=len(files),
        segments=len(segments),
        resources=len(resources),
        content_bytes=content_bytes,
    )


__all__ = [
    "OperationScope",
    "StoreSnapshot",
    "memory_operation",
    "snapshot_store",
    "traced_embed",
]
