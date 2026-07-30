"""Entry-point instrumentation for the memU CLI.

Wraps a CLI invocation in a single SERVER-kind span that represents memU serving
one memory request. The span is parented to the caller's trace (extracted from
``TRACEPARENT``) when present, so the ``memory.*`` spans the operation emits nest
into one end-to-end ``agent → memory`` trace instead of standing alone.

This is also where the SDK gets wired up for the CLI: the library only depends on
``opentelemetry-api`` and never auto-exports, so a real ``memu`` invocation is a
no-op until an OTLP endpoint is configured (``config.otel_enabled()``).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from opentelemetry.trace import SpanKind

from memu.observability import config, providers, semconv
from memu.observability.propagation import extract_context_from_env
from memu.observability.telemetry import init_telemetry


@contextmanager
def cli_telemetry(command: str) -> Iterator[None]:
    """Instrument one CLI command as a SERVER span under any inbound trace.

    A no-op (and zero-overhead beyond the env check) unless telemetry is enabled.
    Flushes on exit so a short-lived CLI process exports before it exits.
    """
    if not config.otel_enabled():
        yield
        return

    handle = init_telemetry()
    try:
        parent = extract_context_from_env()
        tracer = providers.get_tracer("memu.cli", semconv.SEMCONV_VERSION)
        with tracer.start_as_current_span(
            f"memu.{command}",
            context=parent,
            kind=SpanKind.SERVER,
        ) as span:
            span.set_attribute(semconv.ATTR_SUT_NAME, semconv.SUT_NAME)
            span.set_attribute(semconv.ATTR_OPERATION, command)
            yield
    finally:
        handle.shutdown()


__all__ = ["cli_telemetry"]
