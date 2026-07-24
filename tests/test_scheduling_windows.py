"""The Windows Task Scheduler bridging helper (memU#538/#539).

Two things are proven here without touching Task Scheduler or PowerShell — so the
suite is identical on the Windows dev box and a Linux CI runner:

1. the pure builders emit the right scripts (canonical name, S4U, prompt kept off
   the command line), and
2. the ``schedule`` verb is wired in, refuses a host that hasn't opted in, and on
   a non-Windows OS points at cron/launchd instead of touching them.

The OS-executing paths (`install`/`uninstall`/`status`/`verify`) are only reached
behind a ``platform.system() == "Windows"`` gate, exercised here by patching that
gate — never by really registering a task.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from memu.hosts.bridging import Layout
from memu.hosts.claude_code.cli import SPEC as CLAUDE
from memu.hosts.codex.cli import SPEC as CODEX
from memu.hosts.host_cli import build_parser, run
from memu.hosts.scheduling import prompt, windows

# ---------------------------------------------------------------------------
# Pure builders
# ---------------------------------------------------------------------------


def test_powershell_invocation_maps_prompt_placeholder() -> None:
    assert windows.powershell_invocation("C:\\bin\\claude.exe", "claude -p {prompt}") == (
        "& 'C:\\bin\\claude.exe' -p $prompt"
    )
    # The per-host bit is data: a different binary/flag just flows through.
    assert windows.powershell_invocation("/x/codex", "codex exec {prompt}") == "& '/x/codex' exec $prompt"


def test_agent_check_argv_substitutes_probe_prompt() -> None:
    assert windows.agent_check_argv("C:\\bin\\claude.exe", "claude -p {prompt}", "ping") == [
        "C:\\bin\\claude.exe",
        "-p",
        "ping",
    ]


def test_wrapper_keeps_prompt_off_the_command_line(tmp_path: Path) -> None:
    prompt_file = tmp_path / "bridge-prompt.txt"
    log = tmp_path / "bridge.log"
    text = windows.wrapper_script(
        "C:\\bin\\claude.exe", "claude -p {prompt}", prompt_file, log, ["C:\\bin", "C:\\memu"]
    )
    # The prompt is read from the file into $prompt, then passed as one argument —
    # this is the whole point (memU#539): nothing long ever hits the command line.
    assert "Get-Content -Raw" in text
    assert str(prompt_file) in text
    assert "& 'C:\\bin\\claude.exe' -p $prompt" in text
    # PATH is re-established for the scheduler's bare environment (#530, ported).
    assert "$env:Path = 'C:\\bin;C:\\memu;' + $env:Path" in text


def test_register_script_is_canonical_and_hardened() -> None:
    script = windows.register_script("memu-bridging-claude-code", Path("C:\\w\\memu-bridge.ps1"), 60)
    assert "memu-bridging-claude-code" in script
    assert windows.TASK_PATH in script
    assert "-LogonType S4U" in script  # windowless + runs whether logged on or not
    assert "-StartWhenAvailable" in script  # catch up a missed run
    assert "New-TimeSpan -Minutes 60" in script
    assert (
        "-RepetitionDuration (New-TimeSpan -Days 3650)" in script
    )  # ~forever; MaxValue is out-of-range on Win11 (#539)
    assert "memu-bridge.ps1" in script


def test_uninstall_and_status_address_the_same_name() -> None:
    # Deterministic uninstall (memU#539) hinges on all three verbs naming one task.
    name = "memu-bridging-claude-code"
    assert name in windows.unregister_script(name)
    assert name in windows.status_script(name)


def test_task_name_is_canonical_per_host() -> None:
    assert CLAUDE.task_name == "memu-bridging-claude-code"
    assert CODEX.task_name == "memu-bridging-codex"


def test_pipeline_prompt_is_verbatim_but_parameterized() -> None:
    cc = prompt.bridging_pipeline_prompt(CLAUDE)
    for label in ("LEFTOVERS", "PREPARE", "SELF-EVOLVE", "COMMIT"):
        assert label in cc
    assert "memu-claude-code prepare" in cc
    assert "memu-claude-code commit" in cc
    assert "~/.memu/hosts/claude-code/jobs/" in cc
    # The binary tracks the host — the one text serves every adapter.
    assert "memu-codex prepare" in prompt.bridging_pipeline_prompt(CODEX)


# ---------------------------------------------------------------------------
# Verb wiring + guards (no Task Scheduler touched)
# ---------------------------------------------------------------------------


def test_schedule_verb_is_wired() -> None:
    parser = build_parser(CLAUDE)
    args = parser.parse_args(["schedule", "install"])
    assert callable(args.handler)
    assert args.action == "install"
    assert args.interval == 60
    assert parser.parse_args(["schedule", "install", "--interval", "30"]).interval == 30
    with pytest.raises(SystemExit):
        parser.parse_args(["schedule", "frobnicate"])


def test_schedule_refuses_host_without_a_command(capsys: pytest.CaptureFixture[str]) -> None:
    unwired = dataclasses.replace(CLAUDE, schedule_command="")
    assert run(unwired, ["schedule", "status"]) == 2
    assert "no scheduled-run command" in capsys.readouterr().err


def test_schedule_points_at_cron_off_windows(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import memu.hosts.host_cli as host_cli

    monkeypatch.setattr(host_cli.platform, "system", lambda: "Linux")
    assert run(CLAUDE, ["schedule", "status"]) == 0
    assert "cron or launchd" in capsys.readouterr().out


def test_execution_entry_points_are_windows_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(windows.platform, "system", lambda: "Linux")
    layout = Layout.default(host=CLAUDE.host, base=tmp_path)
    for call in (
        lambda: windows.install(CLAUDE, layout),
        lambda: windows.uninstall(CLAUDE, layout),
        lambda: windows.status(CLAUDE, layout),
        lambda: windows.verify(CLAUDE, layout),
    ):
        with pytest.raises(RuntimeError):
            call()


def test_builders_escape_single_quotes_in_paths() -> None:
    # A username with an apostrophe (C:\Users\O'Brien) must not break the
    # single-quoted PowerShell literals — every embedded ' is doubled.
    assert windows.powershell_invocation("C:\\Users\\O'Brien\\claude.exe", "claude -p {prompt}") == (
        "& 'C:\\Users\\O''Brien\\claude.exe' -p $prompt"
    )
    assert "O''Brien" in windows.register_script("t", Path("C:\\O'Brien\\memu-bridge.ps1"), 60)
    assert "O''Brien" in windows.wrapper_script(
        "C:\\O'Brien\\c.exe",
        "claude -p {prompt}",
        Path("C:\\O'Brien\\p.txt"),
        Path("C:\\O'Brien\\l.log"),
        ["C:\\O'Brien"],
    )


def test_pipeline_prompt_matches_the_bridging_doc() -> None:
    # The prompt exists twice — this code builder and the doc's cron block — and the
    # PR promised they stay verbatim. Lock it here: drift fails a test, not silently later.
    from importlib.resources import files

    doc = (files("memu.hosts.claude_code") / "BRIDGING_TASK.md").read_text(encoding="utf-8")
    cron_line = next(line for line in doc.splitlines() if "claude -p 'Run the memU" in line)
    doc_prompt = cron_line.split("claude -p '", 1)[1].rstrip()
    assert doc_prompt.endswith("'")
    assert doc_prompt[:-1] == prompt.bridging_pipeline_prompt(CLAUDE)


def test_install_rejects_nonpositive_interval(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Pretend we're on Windows so the interval guard (not the platform gate) fires;
    # `New-TimeSpan -Minutes 0` is an invalid trigger, so reject before Task Scheduler.
    monkeypatch.setattr(windows.platform, "system", lambda: "Windows")
    layout = Layout.default(host=CLAUDE.host, base=tmp_path)
    assert windows.install(CLAUDE, layout, interval_minutes=0) == 2
    assert "positive" in capsys.readouterr().err


def test_auth_gate_warns_that_credential_must_persist(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # A pass is necessary but not sufficient: the S4U task won't see a session-only
    # $env: token, so even the passing path must tell the user to persist it (#538 B).
    monkeypatch.setattr(windows, "_authenticates", lambda spec, path: (True, ""))
    assert windows._auth_gate(CLAUDE, "C:\\claude.exe") == 0
    assert "PERSISTENT" in capsys.readouterr().err


def test_auth_gate_aborts_when_unauthenticated(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(windows, "_authenticates", lambda spec, path: (False, "Not logged in"))
    assert windows._auth_gate(CLAUDE, "C:\\claude.exe") == 1
    err = capsys.readouterr().err
    assert "setup-token" in err and "PERSISTENT" in err
