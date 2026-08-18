"""W3C trace-context propagation across memU's process boundary.

memU's core is invoked as a subprocess/CLI by an agent (or a host adapter), so
the agent→memory boundary is a process launch, not an HTTP call. The OTel-idiomatic
way to carry a trace across that boundary is the ``TRACEPARENT`` / ``TRACESTATE``
environment variables: the caller injects them, memU extracts them and parents its
``memory.*`` spans under the caller's span — turning disconnected single-op traces
into one end-to-end ``agent → memory`` trace.

These helpers wrap the standard W3C ``tracecontext`` propagator so both sides
(the agent injecting, memU extracting) speak the same format.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from opentelemetry.context import Context
from opentelemetry.propagate import extract, inject

# Env-var names for the W3C carrier (traceparent/tracestate), matched
# case-insensitively — the convention shell/CI propagation already uses.
ENV_TRACEPARENT = "TRACEPARENT"
ENV_TRACESTATE = "TRACESTATE"


def _carrier_from_env(environ: Mapping[str, str]) -> dict[str, str]:
    carrier: dict[str, str] = {}
    traceparent = environ.get(ENV_TRACEPARENT) or environ.get("traceparent")
    tracestate = environ.get(ENV_TRACESTATE) or environ.get("tracestate")
    if traceparent:
        carrier["traceparent"] = traceparent
    if tracestate:
        carrier["tracestate"] = tracestate
    return carrier


def extract_context_from_env(environ: Mapping[str, str] | None = None) -> Context | None:
    """Extract the caller's trace context from ``TRACEPARENT``/``TRACESTATE``.

    Returns ``None`` when no ``traceparent`` is present (so callers can start a
    fresh root trace), otherwise the remote :class:`Context` to parent under.
    """
    carrier = _carrier_from_env(os.environ if environ is None else environ)
    if "traceparent" not in carrier:
        return None
    return extract(carrier)


def env_with_current_context(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return a copy of ``environ`` with the *current* span's W3C headers injected.

    Used by a caller (agent / host adapter) to propagate its active trace into a
    memU subprocess: ``subprocess.run(["memu", ...], env=env_with_current_context())``.
    """
    result = dict(os.environ if environ is None else environ)
    carrier: dict[str, str] = {}
    inject(carrier)
    if "traceparent" in carrier:
        result[ENV_TRACEPARENT] = carrier["traceparent"]
    if "tracestate" in carrier:
        result[ENV_TRACESTATE] = carrier["tracestate"]
    return result


__all__ = [
    "ENV_TRACEPARENT",
    "ENV_TRACESTATE",
    "env_with_current_context",
    "extract_context_from_env",
]
