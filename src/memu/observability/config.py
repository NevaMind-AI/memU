"""Environment-driven configuration for memU's OpenTelemetry instrumentation.

memU is a *library*: it depends only on ``opentelemetry-api`` (a no-op unless an
SDK is installed and wired up) and never auto-starts an exporter. The embedding
app, a host adapter, or the benchmark harness calls
:func:`memu.observability.init_telemetry` to turn signals on. These helpers read
the knobs that shape that call.
"""

from __future__ import annotations

import os

# Master switch. Instrumentation code (spans/metrics) is always *present* and
# cheap when no SDK is configured, so this only gates the SDK wiring done by
# ``init_telemetry`` when it is asked to build exporters from the environment.
ENV_ENABLED = "MEMU_OTEL_ENABLED"

# Opt-in for capturing the raw search query as the ``memory.query.text`` span
# attribute. memory-semconv v0.1.0 §2.4 forbids it by default (PII risk); we
# always emit the PII-safe ``memory.query.length`` instead. Turning this on is a
# deliberate operator choice that assumes collector-side scrubbing is in place.
ENV_CAPTURE_QUERY_TEXT = "MEMU_OTEL_CAPTURE_QUERY_TEXT"

# Overrides the ``memory.sut.store_backend`` resource attribute. Handy when the
# process fronts a backend whose kind isn't otherwise discoverable at init time.
ENV_STORE_BACKEND = "MEMU_OTEL_STORE_BACKEND"

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUTHY


def otel_enabled() -> bool:
    """Whether ``init_telemetry`` should wire SDK exporters from the environment.

    Defaults to on when the standard ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set (the
    conventional signal that a collector is reachable), and can be forced either
    way with :data:`ENV_ENABLED`.
    """
    if ENV_ENABLED in os.environ:
        return _flag(ENV_ENABLED)
    return bool(os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"))


def capture_query_text() -> bool:
    """Whether the raw query text may be attached to read spans (default: no)."""
    return _flag(ENV_CAPTURE_QUERY_TEXT)


def store_backend_override() -> str | None:
    value = os.environ.get(ENV_STORE_BACKEND)
    return value.strip() or None if value else None


__all__ = [
    "ENV_CAPTURE_QUERY_TEXT",
    "ENV_ENABLED",
    "ENV_STORE_BACKEND",
    "capture_query_text",
    "otel_enabled",
    "store_backend_override",
]
