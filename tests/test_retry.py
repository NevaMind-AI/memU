"""HTTP Retry-After parsing for both cloud and embedding clients."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx
import pytest

import memu.retry as retry


@pytest.mark.parametrize("server_date", [None, "not-a-date"])
def test_http_date_retry_after_without_valid_response_date(
    monkeypatch: pytest.MonkeyPatch, server_date: str | None
) -> None:
    now = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)

    class FixedDateTime:
        @staticmethod
        def now(tz: timezone) -> datetime:
            assert tz == timezone.utc
            return now

    monkeypatch.setattr(retry, "datetime", FixedDateTime)

    headers = {"Retry-After": format_datetime(now + timedelta(seconds=12), usegmt=True)}
    if server_date is not None:
        headers["Date"] = server_date
    assert retry.retry_delay(1, httpx.Response(429, headers=headers)) == 12.0


def test_http_date_retry_after_prefers_response_date() -> None:
    server_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    response = httpx.Response(
        429,
        headers={
            "Date": format_datetime(server_time, usegmt=True),
            "Retry-After": format_datetime(server_time + timedelta(seconds=9), usegmt=True),
        },
    )
    assert retry.retry_delay(1, response) == 9.0


def test_http_date_retry_after_is_capped_to_thirty_seconds() -> None:
    server_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    response = httpx.Response(
        429,
        headers={
            "Date": format_datetime(server_time, usegmt=True),
            "Retry-After": format_datetime(server_time + timedelta(minutes=2), usegmt=True),
        },
    )
    assert retry.retry_delay(1, response) == 30.0


def test_invalid_retry_after_uses_exponential_backoff() -> None:
    response = httpx.Response(429, headers={"Retry-After": "definitely-not-a-date"})
    assert retry.retry_delay(1, response) == 0.25
