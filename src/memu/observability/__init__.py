"""OpenTelemetry instrumentation for memU (memory-semconv v0.1.0).

The public surface is small on purpose:

* :func:`init_telemetry` / :func:`shutdown_telemetry` — wire (and tear down) the
  SDK. memU itself only depends on ``opentelemetry-api``; without an SDK these
  stay no-ops.
* :func:`memory_operation` / :func:`traced_embed` — the instrumentation the
  ``AgenticMixin`` wraps its operations in.
* :mod:`memu.observability.semconv` — the naming contract (span, attribute, and
  metric names), importable as ``from memu.observability import semconv``.
"""

from __future__ import annotations

from memu.observability import config, semconv
from memu.observability.instruments import (
    record_embed_tokens,
    record_operation_duration,
    record_recall_results,
    register_volume_source,
)
from memu.observability.operation import (
    OperationScope,
    StoreSnapshot,
    memory_operation,
    snapshot_store,
    traced_embed,
)
from memu.observability.telemetry import (
    TelemetryHandle,
    get_telemetry_handle,
    init_telemetry,
    shutdown_telemetry,
)

__all__ = [
    "OperationScope",
    "StoreSnapshot",
    "TelemetryHandle",
    "config",
    "get_telemetry_handle",
    "init_telemetry",
    "memory_operation",
    "record_embed_tokens",
    "record_operation_duration",
    "record_recall_results",
    "register_volume_source",
    "semconv",
    "shutdown_telemetry",
    "snapshot_store",
    "traced_embed",
]
