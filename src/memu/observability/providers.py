"""Provider registry so memU's instrumentation isn't tied to OTel's globals.

OpenTelemetry only lets a process install a *global* TracerProvider /
MeterProvider once, which makes per-run reconfiguration (and test isolation)
impossible through the globals alone. memU's :func:`init_telemetry` therefore
records the providers it built *here*, and the span/metric emitters read the
active provider from this module — falling back to the OTel global (a no-op
until an SDK is installed) when memU hasn't wired anything up.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from opentelemetry import metrics, trace

if TYPE_CHECKING:
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.trace import TracerProvider

_tracer_provider: TracerProvider | None = None
_meter_provider: MeterProvider | None = None


def set_providers(tracer_provider: TracerProvider, meter_provider: MeterProvider) -> None:
    global _tracer_provider, _meter_provider
    _tracer_provider = tracer_provider
    _meter_provider = meter_provider


def clear_providers() -> None:
    global _tracer_provider, _meter_provider
    _tracer_provider = None
    _meter_provider = None


def get_tracer(name: str, version: str) -> trace.Tracer:
    if _tracer_provider is not None:
        return _tracer_provider.get_tracer(name, version)
    return trace.get_tracer(name, version)


def get_meter(name: str, version: str) -> metrics.Meter:
    if _meter_provider is not None:
        return _meter_provider.get_meter(name, version)
    return metrics.get_meter(name, version)


__all__ = ["clear_providers", "get_meter", "get_tracer", "set_providers"]
