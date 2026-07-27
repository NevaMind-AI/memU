"""Metric instruments for memU, named per memory-semconv v0.1.0.

Instruments are created lazily against the active ``MeterProvider`` (memU's own,
via :mod:`memu.observability.providers`, falling back to the OTel global), so
importing this module is free and safe even when no SDK is wired up — the API
hands back no-op instruments. The data-volume gauges are *observable*: their
callbacks read live counts from registered stores only at the meter's collection
interval, keeping the O(n) count off the request path.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from opentelemetry.metrics import CallbackOptions, Observation

from memu.observability import providers, semconv

_INSTRUMENTATION_SCOPE = "memu.observability"
_LOG = logging.getLogger("memu.observability")

# A source of live volume for one store: returns (store_kind, items, bytes).
VolumeSource = Callable[[], "tuple[str, int, int]"]

_volume_sources: list[VolumeSource] = []
_instruments: dict[str, Any] | None = None


def _reject_bad_labels(labels: Mapping[str, Any]) -> None:
    """Guard the spec's cardinality budget (§2.1 rule 4) at the call site."""
    extra = set(labels) - semconv.ALLOWED_METRIC_LABELS
    if extra:
        msg = f"disallowed metric label(s) {sorted(extra)}; allowed: {sorted(semconv.ALLOWED_METRIC_LABELS)}"
        raise ValueError(msg)


def register_volume_source(source: VolumeSource) -> None:
    """Register a callable feeding the ``memory_items_total``/``_bytes_total`` gauges.

    Idempotent by identity, so a service can call it on every operation without
    piling up duplicate observations.
    """
    if source not in _volume_sources:
        _volume_sources.append(source)


def _read_sources() -> list[tuple[str, int, int]]:
    """Poll every registered volume source, skipping (and logging) broken ones.

    A source that raises must not abort the whole metric collection cycle, so we
    isolate each one — but we log it rather than swallowing it silently.
    """
    readings: list[tuple[str, int, int]] = []
    for source in list(_volume_sources):
        try:
            readings.append(source())
        except Exception:
            _LOG.debug("volume source raised; skipping it for this collection", exc_info=True)
    return readings


def _observe_items(_options: CallbackOptions) -> Iterable[Observation]:
    for store_kind, items, _bytes in _read_sources():
        yield Observation(
            items,
            {semconv.METRIC_LABEL_STORE_KIND: store_kind, semconv.METRIC_LABEL_SUT_NAME: semconv.SUT_NAME},
        )


def _observe_bytes(_options: CallbackOptions) -> Iterable[Observation]:
    for store_kind, _items, byte_count in _read_sources():
        yield Observation(
            byte_count,
            {semconv.METRIC_LABEL_STORE_KIND: store_kind, semconv.METRIC_LABEL_SUT_NAME: semconv.SUT_NAME},
        )


def _build_instruments() -> dict[str, Any]:
    meter = providers.get_meter(_INSTRUMENTATION_SCOPE, semconv.SEMCONV_VERSION)
    duration = meter.create_histogram(
        semconv.METRIC_OPERATION_DURATION,
        unit="s",
        description="Duration of a memory operation (write/search/list).",
    )
    recall_results = meter.create_histogram(
        semconv.METRIC_RECALL_RESULTS_COUNT,
        unit="{item}",
        description="Number of results a recall (search/list) returned.",
    )
    embed_tokens = meter.create_counter(
        semconv.METRIC_EMBED_TOKEN_TOTAL,
        unit="{token}",
        description="Embedding tokens consumed by memory operations.",
    )
    # Observable gauges: registered once, fed by _volume_sources at collection.
    meter.create_observable_gauge(
        semconv.METRIC_ITEMS_TOTAL,
        callbacks=[_observe_items],
        unit="{item}",
        description="Logical memory items (recall files + resources) held per store.",
    )
    meter.create_observable_gauge(
        semconv.METRIC_BYTES_TOTAL,
        callbacks=[_observe_bytes],
        unit="By",
        description="Bytes of memory content held per store.",
    )
    return {"duration": duration, "recall_results": recall_results, "embed_tokens": embed_tokens}


def _get() -> dict[str, Any]:
    global _instruments
    if _instruments is None:
        _instruments = _build_instruments()
    return _instruments


def reset_instruments() -> None:
    """Drop cached instruments so the next use binds to a fresh MeterProvider.

    Meant for tests that install a new provider between cases; also clears the
    volume-source registry so gauges don't observe a torn-down store.
    """
    global _instruments
    _instruments = None
    _volume_sources.clear()


def record_operation_duration(operation: str, store_kind: str, seconds: float) -> None:
    labels = {
        semconv.METRIC_LABEL_OPERATION: operation,
        semconv.METRIC_LABEL_STORE_KIND: store_kind,
        semconv.METRIC_LABEL_SUT_NAME: semconv.SUT_NAME,
    }
    _reject_bad_labels(labels)
    _get()["duration"].record(seconds, labels)


def record_recall_results(store_kind: str, count: int) -> None:
    labels = {
        semconv.METRIC_LABEL_STORE_KIND: store_kind,
        semconv.METRIC_LABEL_SUT_NAME: semconv.SUT_NAME,
    }
    _reject_bad_labels(labels)
    _get()["recall_results"].record(count, labels)


def record_embed_tokens(embedder_model: str, tokens: int) -> None:
    if tokens <= 0:
        return
    labels = {
        semconv.METRIC_LABEL_SUT_NAME: semconv.SUT_NAME,
        semconv.METRIC_LABEL_EMBEDDER_MODEL: embedder_model,
    }
    _reject_bad_labels(labels)
    _get()["embed_tokens"].add(tokens, labels)


__all__ = [
    "record_embed_tokens",
    "record_operation_duration",
    "record_recall_results",
    "register_volume_source",
    "reset_instruments",
]
