"""SDK bootstrap for memU's OpenTelemetry signals.

memU ships only the ``opentelemetry-api`` dependency; installing an SDK and
calling :func:`init_telemetry` is what turns spans/metrics/logs from no-ops into
exported data. The app, a host adapter, or the benchmark harness calls this once
at startup. Tests call it with in-memory exporters/readers to assert on emitted
signals without a collector.

Exporter wiring is optional and lazy: if no exporter is passed and the
environment names no OTLP endpoint, providers are still installed (so the API
records) but nothing is shipped — the caller opted out of export, not out of
instrumentation.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

from opentelemetry import metrics, trace
from opentelemetry._logs import get_logger_provider, set_logger_provider

from memu.observability import config, instruments, providers, semconv

# The SDK ships in memU's optional ``observability`` extra; the library itself
# hard-depends only on ``opentelemetry-api``. Import SDK symbols lazily inside
# the functions that install providers, so that merely importing this module
# (which ``memu.cli`` and ``memu.observability`` do at load time) never requires
# the SDK. With ``from __future__ import annotations`` the type references below
# are strings, resolved by type-checkers only — never at runtime.
if TYPE_CHECKING:
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler, LogRecordProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import MetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SpanExporter, SpanProcessor

_LOG_LOGGER_NAME = "memu.observability"


@dataclass
class TelemetryHandle:
    """Handles to the installed providers, so a caller can flush and shut down."""

    tracer_provider: TracerProvider
    meter_provider: MeterProvider
    logger_provider: LoggerProvider
    logging_handler: LoggingHandler

    def shutdown(self) -> None:
        """Flush and tear down every provider; detach the logging bridge."""
        logging.getLogger(_LOG_LOGGER_NAME).removeHandler(self.logging_handler)
        providers.clear_providers()
        self.tracer_provider.shutdown()
        self.meter_provider.shutdown()
        self.logger_provider.shutdown()
        instruments.reset_instruments()


_handle: TelemetryHandle | None = None


def _memu_version() -> str:
    try:
        return version("memu-cli")
    except PackageNotFoundError:  # pragma: no cover - only when run from a non-install tree
        return "unknown"


def build_resource(resource_attributes: Mapping[str, str] | None, store_backend: str | None) -> Resource:
    """Assemble the per-process resource with the ``memory.sut.*`` identity."""
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource

    attrs: dict[str, Any] = {
        SERVICE_NAME: semconv.SUT_NAME,
        semconv.ATTR_SUT_NAME: semconv.SUT_NAME,
        semconv.ATTR_SUT_VERSION: _memu_version(),
        semconv.ATTR_SUT_ARCHITECTURE: semconv.SUT_ARCHITECTURE,
    }
    backend = store_backend or config.store_backend_override()
    if backend:
        attrs[semconv.ATTR_SUT_STORE_BACKEND] = backend
    if resource_attributes:
        attrs.update(resource_attributes)
    return Resource.create(attrs)


def _otlp_span_exporter() -> SpanExporter | None:
    if not config.otel_enabled():
        return None
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    return OTLPSpanExporter()


def _otlp_metric_reader() -> MetricReader | None:
    if not config.otel_enabled():
        return None
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

    return PeriodicExportingMetricReader(OTLPMetricExporter())


def _otlp_log_processor() -> LogRecordProcessor | None:
    if not config.otel_enabled():
        return None
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

    return BatchLogRecordProcessor(OTLPLogExporter())


def init_telemetry(
    *,
    resource_attributes: Mapping[str, str] | None = None,
    store_backend: str | None = None,
    span_exporter: SpanExporter | None = None,
    metric_reader: MetricReader | None = None,
    log_processor: LogRecordProcessor | None = None,
    set_global: bool = True,
    force: bool = False,
) -> TelemetryHandle:
    """Install tracer/meter/logger providers for memU and return their handle.

    Idempotent: a second call returns the existing handle unless ``force`` is
    set. Pass explicit ``span_exporter`` / ``metric_reader`` / ``log_processor``
    (e.g. in-memory ones) to capture signals in-process; omit them to wire OTLP
    exporters from the standard ``OTEL_EXPORTER_OTLP_*`` environment when
    :func:`config.otel_enabled` is true.
    """
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    global _handle
    if _handle is not None and not force:
        return _handle
    if _handle is not None and force:
        _handle.shutdown()
        _handle = None
    instruments.reset_instruments()

    resource = build_resource(resource_attributes, store_backend)

    tracer_provider = TracerProvider(resource=resource)
    span_processor: SpanProcessor | None = None
    exporter = span_exporter or _otlp_span_exporter()
    if exporter is not None:
        span_processor = BatchSpanProcessor(exporter)
        tracer_provider.add_span_processor(span_processor)

    reader = metric_reader or _otlp_metric_reader()
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader] if reader is not None else [])

    logger_provider = LoggerProvider(resource=resource)
    processor = log_processor or _otlp_log_processor()
    if processor is not None:
        logger_provider.add_log_record_processor(processor)

    # Always register with memU's own provider registry: the instrumentation
    # reads providers from there, so it works even when we don't (or can't,
    # OTel allows it once) install the process globals.
    providers.set_providers(tracer_provider, meter_provider)
    if set_global:
        trace.set_tracer_provider(tracer_provider)
        metrics.set_meter_provider(meter_provider)
        set_logger_provider(logger_provider)

    # Bridge stdlib logs from the operation module into OTel LogRecords, so the
    # per-operation logs carry the active span's trace/span id automatically.
    logging_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    op_logger = logging.getLogger(_LOG_LOGGER_NAME)
    op_logger.setLevel(logging.INFO)
    op_logger.addHandler(logging_handler)

    handle = TelemetryHandle(
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        logger_provider=logger_provider,
        logging_handler=logging_handler,
    )
    if set_global:
        _handle = handle
    # Ensure freshly-built instruments bind to this MeterProvider.
    instruments.reset_instruments()
    return handle


def get_telemetry_handle() -> TelemetryHandle | None:
    """The globally-installed handle, or ``None`` if ``init_telemetry`` hasn't run."""
    return _handle


def shutdown_telemetry() -> None:
    """Shut down the globally-installed telemetry, if any."""
    global _handle
    if _handle is not None:
        _handle.shutdown()
        _handle = None


__all__ = [
    "TelemetryHandle",
    "build_resource",
    "get_logger_provider",
    "get_telemetry_handle",
    "init_telemetry",
    "shutdown_telemetry",
]
