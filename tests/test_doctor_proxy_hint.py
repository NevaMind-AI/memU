"""A failed doctor should diagnose proxy trouble, not just print a bare 502.

Field origin: a live install against local Ollama spent minutes of agent tool
calls ruling out cold-start, IPv6, and header theories before finding a proxy
configured only in macOS's system-wide settings — invisible to ``env``. Every
fact in that conclusion was free to check at failure time; these pin that the
doctor now checks them and says what they imply.
"""

from __future__ import annotations

import argparse
import os
import urllib.request

import pytest

from memu.hosts import retrieval
from memu.hosts.codex.cli import SPEC
from memu.hosts.host_cli import _cmd_doctor, _proxy_hint

PROXY = "http://proxy.corp:8080"
LOOPBACK = "http://localhost:11434/v1"


@pytest.fixture(autouse=True)
def _clean_proxy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.lower().endswith("_proxy") or key.lower() == "no_proxy":
            monkeypatch.delenv(key, raising=False)
    # macOS reads system-wide proxies through getproxies(); pin to env-only so
    # these tests behave the same on a developer machine with a system proxy.
    monkeypatch.setattr(urllib.request, "getproxies", urllib.request.getproxies_environment)


def test_no_proxies_no_hint() -> None:
    assert _proxy_hint(LOOPBACK) is None


def test_loopback_with_ambient_proxy_points_at_the_server(monkeypatch: pytest.MonkeyPatch) -> None:
    """With the automatic bypass in this build, the proxy is likely NOT the
    cause — the hint should steer the agent away from the proxy rabbit hole."""
    monkeypatch.setenv("HTTP_PROXY", PROXY)
    hint = _proxy_hint(LOOPBACK)
    assert hint is not None
    assert "bypasses proxies for loopback" in hint
    assert "the shell environment" in hint
    assert "NO_PROXY" in hint, "older releases still need the exemption"


def test_os_level_proxy_is_named_as_the_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """The field case: getproxies() reports a proxy while env shows nothing —
    macOS system settings. The hint must name that source explicitly."""
    monkeypatch.setattr(urllib.request, "getproxies", lambda: {"http": PROXY})
    hint = _proxy_hint(LOOPBACK)
    assert hint is not None
    assert "system-wide settings" in hint
    assert "invisible to `env`" in hint


def test_explicit_memu_proxy_is_called_out(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMU_HTTP_PROXY", PROXY)
    hint = _proxy_hint(LOOPBACK)
    assert hint is not None
    assert "MEMU_HTTP_PROXY" in hint


def test_non_loopback_local_address_suggests_no_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", PROXY)
    hint = _proxy_hint("http://host.docker.internal:11434/v1")
    assert hint is not None
    assert "host.docker.internal" in hint
    assert "NO_PROXY" in hint


async def test_doctor_prints_hint_on_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MEMU_BASE_URL", LOOPBACK)
    monkeypatch.setenv("HTTP_PROXY", PROXY)
    monkeypatch.delenv("MEMU_DEBUG", raising=False)

    async def boom(query: str) -> dict:
        raise RuntimeError("502")

    monkeypatch.setattr(retrieval, "retrieve", boom)

    rc = await _cmd_doctor(SPEC, argparse.Namespace())

    assert rc == 1
    err = capsys.readouterr().err
    assert "error: 502" in err
    assert "hint:" in err


async def test_doctor_failure_without_proxies_has_no_hint(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MEMU_BASE_URL", LOOPBACK)
    monkeypatch.delenv("MEMU_DEBUG", raising=False)

    async def boom(query: str) -> dict:
        raise RuntimeError("502")

    monkeypatch.setattr(retrieval, "retrieve", boom)

    rc = await _cmd_doctor(SPEC, argparse.Namespace())

    assert rc == 1
    err = capsys.readouterr().err
    assert "error: 502" in err
    assert "hint:" not in err


async def test_config_error_gets_no_proxy_hint_even_with_proxies(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing MEMU_DB has nothing to do with proxies — on a VPN machine
    (proxies always detected) the hint must not fire on every failure."""
    from memu.env import ConfigError

    monkeypatch.setenv("MEMU_BASE_URL", LOOPBACK)
    monkeypatch.setenv("HTTP_PROXY", PROXY)
    monkeypatch.delenv("MEMU_DEBUG", raising=False)

    async def boom(query: str) -> dict:
        raise ConfigError("MEMU_DB")

    monkeypatch.setattr(retrieval, "retrieve", boom)

    assert await _cmd_doctor(SPEC, argparse.Namespace()) == 1
    assert "hint:" not in capsys.readouterr().err


async def test_auth_error_gets_no_proxy_hint(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MEMU_BASE_URL", LOOPBACK)
    monkeypatch.setenv("HTTP_PROXY", PROXY)
    monkeypatch.delenv("MEMU_DEBUG", raising=False)

    async def boom(query: str) -> dict:
        raise RuntimeError("401")

    monkeypatch.setattr(retrieval, "retrieve", boom)

    assert await _cmd_doctor(SPEC, argparse.Namespace()) == 1
    assert "hint:" not in capsys.readouterr().err


async def test_wrapped_transport_error_still_hints(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The interesting error is usually wrapped by the SDK — the gate must
    walk the cause chain, not just look at the outermost message."""
    monkeypatch.setenv("MEMU_BASE_URL", LOOPBACK)
    monkeypatch.setenv("HTTP_PROXY", PROXY)
    monkeypatch.delenv("MEMU_DEBUG", raising=False)

    class ConnectError(Exception):
        pass

    async def boom(query: str) -> dict:
        raise RuntimeError("failed") from ConnectError()

    monkeypatch.setattr(retrieval, "retrieve", boom)

    assert await _cmd_doctor(SPEC, argparse.Namespace()) == 1
    assert "hint:" in capsys.readouterr().err
