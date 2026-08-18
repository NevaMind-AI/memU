"""Shared retry policy for memU's outbound HTTP clients.

Every client that talks to a third party over HTTP — the cloud memory transport
and the embedding transports — faces the same transient failures: a dropped
connection, a rate limit, a provider 5xx. Encoding "which of those are worth
retrying, and how long to wait" once keeps the clients from drifting into
separate dialects, so a ``Retry-After`` honoured in one place is honoured
everywhere.
"""

from __future__ import annotations

from email.utils import parsedate_to_datetime

import httpx

# Statuses a retry can plausibly fix. Everything else — 401 on a bad key, 400 on
# an unknown model, 404 on a wrong endpoint — fails identically on every attempt,
# so retrying only delays the error the caller needs to see.
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

DEFAULT_MAX_ATTEMPTS = 3

# A provider asking for a multi-minute pause is asking for more than any caller
# here is willing to block for; past this we give up rather than hang.
_MAX_RETRY_AFTER = 30.0
_BASE_BACKOFF = 0.25
_MAX_BACKOFF = 2.0


def retry_delay(attempt: int, response: httpx.Response | None = None) -> float:
    """Seconds to wait before retrying, after ``attempt`` (1-based) failed.

    A provider's own ``Retry-After`` wins when it sends one — it knows when its
    rate-limit window reopens and we do not — in either of the header's two
    forms (delta-seconds or an HTTP-date, the latter read against the response's
    own ``Date`` so a skewed local clock cannot turn into a wild sleep). Absent
    or unparseable, fall back to capped exponential backoff.
    """
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(max(float(retry_after), 0.0), _MAX_RETRY_AFTER)
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(retry_after)
                    now = parsedate_to_datetime(response.headers.get("Date", ""))
                    return float(min(max((retry_at - now).total_seconds(), 0.0), _MAX_RETRY_AFTER))
                except (TypeError, ValueError, OverflowError):
                    pass
    return float(min(_BASE_BACKOFF * (2 ** (attempt - 1)), _MAX_BACKOFF))
