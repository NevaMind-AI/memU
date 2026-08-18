"""TLS trust for the two ``urllib`` call sites (:mod:`memu.trust`).

The bug this module exists for was invisible from both ends: a python.org
framework Python with no CA bundle failed verification on every ``urlopen``,
which two fail-open ``except`` clauses turned into "events never delivered" and
"templates never refresh", while the ``httpx`` paths on the same machine kept
working. So these tests are weighted toward the two directions the fix must not
go wrong in — it must fix the vacuum, and it must not touch a machine that
already has a trust store.
"""

from __future__ import annotations

import pathlib
import ssl
import sys
import types
from typing import Any

import pytest

from memu import events, trust
from memu.hosts import templates


@pytest.fixture(autouse=True)
def _uncached() -> Any:
    """:func:`trust.ssl_context` is cached for the life of a process, so every test
    here has to start from an unanswered question — and leave one behind."""
    trust.ssl_context.cache_clear()
    yield
    trust.ssl_context.cache_clear()


def _verify_paths(monkeypatch: pytest.MonkeyPatch, *, cafile: str | None, capath: str | None) -> None:
    monkeypatch.setattr(ssl, "get_default_verify_paths", lambda: types.SimpleNamespace(cafile=cafile, capath=capath))


# --- the machine that already works must not change at all ---


def test_an_existing_trust_store_is_left_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    """The system store wins wherever one exists, and that is not a preference —
    it is what keeps a corporate root CA working. ``certifi`` does not carry one,
    so a machine behind a TLS-inspecting proxy would start failing exactly as
    silently as the bug this fixes if the fallback were a pin instead."""
    _verify_paths(monkeypatch, cafile="/etc/ssl/cert.pem", capath=None)

    assert trust.ssl_context() is None


def test_a_capath_alone_counts_as_a_trust_store(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Linux shape: a hashed directory and no single bundle file."""
    _verify_paths(monkeypatch, cafile=None, capath="/etc/ssl/certs")

    assert trust.ssl_context() is None


def test_no_context_argument_is_passed_when_the_store_is_healthy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Not merely equivalent behaviour — the *same call*.

    An install that works today must be untouched by construction, so the fix
    passes no ``context`` whatsoever rather than passing a reconstructed one that
    is only meant to be identical.
    """
    _verify_paths(monkeypatch, cafile="/etc/ssl/cert.pem", capath=None)

    assert trust.urlopen_kwargs() == {}


# --- the machine with no trust store at all ---


def test_certifi_fills_a_vacuum(monkeypatch: pytest.MonkeyPatch) -> None:
    _verify_paths(monkeypatch, cafile=None, capath=None)

    context = trust.ssl_context()

    assert context is not None
    # Verifying, emphatically: a fallback that filled the vacuum by switching
    # verification off would "fix" the flush and hand the endpoint to anyone on
    # the network path.
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert context.get_ca_certs(), "fallback context carries no CAs"
    assert trust.urlopen_kwargs() == {"context": context}


def test_a_missing_certifi_degrades_instead_of_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    """``certifi`` arrives as an httpx dependency, not one this module declares.

    If it is ever absent the answer is today's behaviour — unverifiable but
    unchanged — because this function sits on two paths whose whole contract is
    that they cannot be the thing that breaks a command.
    """
    _verify_paths(monkeypatch, cafile=None, capath=None)
    monkeypatch.setitem(sys.modules, "certifi", None)

    assert trust.ssl_context() is None
    assert trust.urlopen_kwargs() == {}


def test_the_answer_is_cached_across_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """A flush may POST `MAX_FLUSH_POSTS` times and each miss parses certifi's
    whole PEM bundle, so the same context must come back rather than be rebuilt."""
    _verify_paths(monkeypatch, cafile=None, capath=None)

    assert trust.ssl_context() is trust.ssl_context()


# --- both call sites actually consult it ---


class _Recorder:
    """A ``urlopen`` that records whether it was handed a context."""

    def __init__(self) -> None:
        self.kwargs: dict[str, Any] = {}

    def __call__(self, *args: Any, **kwargs: Any) -> _Recorder:
        self.kwargs = kwargs
        return self

    def read(self, n: int = -1) -> bytes:
        return b""

    status = 200

    def __enter__(self) -> _Recorder:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def test_event_delivery_verifies_against_the_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    _verify_paths(monkeypatch, cafile=None, capath=None)
    recorder = _Recorder()
    monkeypatch.setattr(events.urllib.request, "urlopen", recorder)

    assert events._post("https://example.test/events", {"event_name": "x"}) == events.ACCEPTED
    assert isinstance(recorder.kwargs.get("context"), ssl.SSLContext)


def test_template_refresh_verifies_against_the_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """The second call site, and the reason the fix is one decision rather than two:
    a silent template fallback is the same failure wearing different clothes."""
    _verify_paths(monkeypatch, cafile=None, capath=None)
    recorder = _Recorder()
    monkeypatch.setattr(templates.urllib.request, "urlopen", recorder)

    templates._get("https://example.test/inst/memory-job.txt")

    assert isinstance(recorder.kwargs.get("context"), ssl.SSLContext)
