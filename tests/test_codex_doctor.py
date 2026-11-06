"""Codex doctor diagnoses local integration without changing it."""

import json
from typing import Any

import pytest

from memu.hosts import host_cli
from memu.hosts.codex import doctor, prompt_hook_install
from memu.hosts.codex.cli import SPEC


@pytest.fixture
def integration(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    monkeypatch.setattr(doctor.cli_prepare, "find_executable", lambda: tmp_path / "codex.exe")
    monkeypatch.setattr(doctor.cli_prepare, "prepare", lambda _: {"status": "passed", "version": "codex-cli test"})
    groups: list[dict[str, Any]] = []
    for subcommand in ("prompt-hook", "memorize-hook"):
        prompt_hook_install._definition(groups, f"memu-codex {subcommand}", subcommand)
    path = tmp_path / "hooks.json"
    path.write_text(json.dumps({"hooks": {"UserPromptSubmit": groups}}), encoding="utf-8")
    return path, groups


@pytest.mark.parametrize(
    "problem", ["healthy", "missing-cli", "missing-hooks", "outdated", "fixed-path", "duplicate", "invalid"]
)
def test_local_integration_diagnostics(integration, monkeypatch, capsys, problem):  # noqa: C901
    path, groups = integration
    if problem == "missing-cli":

        def missing():
            raise FileNotFoundError("Standalone Codex CLI unavailable")  # noqa: TRY003

        monkeypatch.setattr(doctor.cli_prepare, "find_executable", missing)
    elif problem == "missing-hooks":
        path.unlink()
    elif problem == "invalid":
        path.write_text("{", encoding="utf-8")
    elif problem == "outdated":
        groups[0]["hooks"][0].pop("async")
    elif problem == "fixed-path":
        groups[1]["hooks"][0]["command"] += " --agent old-codex"
    elif problem == "duplicate":
        groups.append(groups[0])
    if problem in ("outdated", "fixed-path", "duplicate"):
        path.write_text(json.dumps({"hooks": {"UserPromptSubmit": groups}}), encoding="utf-8")
    before = path.read_bytes() if path.exists() else None
    assert doctor.check() == (0 if problem == "healthy" else 1)
    text = capsys.readouterr().out
    if problem == "healthy":
        assert "prompt-hook ok" in text and "memorize-hook ok" in text
        assert "hint:" not in text
    else:
        assert "memu-codex install" in text
    if problem == "missing-cli":
        assert "Standalone Codex CLI unavailable" in text
        assert "prompt-hook ok" in text
    if problem == "missing-hooks":
        assert "prompt-hook missing" in text and "memorize-hook missing" in text
    if problem in ("outdated", "fixed-path", "duplicate"):
        assert "outdated" in text
    assert (path.read_bytes() if path.exists() else None) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("backend_only", [False, True])
@pytest.mark.parametrize("backend_status,integration_status", [(0, 0), (1, 0), (0, 1)])
async def test_backend_and_integration_checks_are_independent(
    monkeypatch, backend_only, backend_status, integration_status
):
    from argparse import Namespace

    async def backend(spec, args):
        return backend_status

    calls = []
    monkeypatch.setattr(host_cli, "_cmd_backend_doctor", backend)

    def integration():
        calls.append("integration")
        return integration_status

    monkeypatch.setattr(doctor, "check", integration)
    expected = backend_status if backend_only else int(bool(backend_status or integration_status))
    assert await host_cli._cmd_doctor(SPEC, Namespace(backend_only=backend_only)) == expected
    assert calls == ([] if backend_only else ["integration"])
