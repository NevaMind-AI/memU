"""The Windows Task Scheduler bridging helper (memU#538/#539).

The pure builders are proven without touching Task Scheduler or PowerShell, so
those checks are identical on the Windows dev box and a Linux CI runner:

1. the pure builders emit the right scripts (canonical name, S4U, prompt kept off
   the command line), and
2. the ``schedule`` verb is wired in, refuses a host that hasn't opted in, and on
   a non-Windows OS points at cron/launchd instead of touching them.

One Windows-only regression test runs a generated wrapper under Windows
PowerShell 5.1 to cover its native-stderr behavior. The OS-executing paths
(`install`/`uninstall`/`status`/`verify`) are still reached only behind a
``platform.system() == "Windows"`` gate, exercised here by patching that gate —
never by really registering a task.
"""

from __future__ import annotations

import dataclasses
import os
import platform
import subprocess
from pathlib import Path

import pytest

from memu.hosts.bridging import Layout
from memu.hosts.claude_code.cli import SPEC as CLAUDE
from memu.hosts.codex.cli import SPEC as CODEX
from memu.hosts.cola.cli import SPEC as COLA
from memu.hosts.cursor.cli import SPEC as CURSOR
from memu.hosts.generic.cli import SPEC as GENERIC
from memu.hosts.hermes.cli import SPEC as HERMES
from memu.hosts.host_cli import ScheduleBackend, build_parser, run
from memu.hosts.openclaw.cli import SPEC as OPENCLAW
from memu.hosts.scheduling import prompt, windows
from memu.hosts.workbuddy.cli import SPEC as WORKBUDDY

# ---------------------------------------------------------------------------
# Pure builders
# ---------------------------------------------------------------------------


def test_powershell_invocation_maps_prompt_placeholder() -> None:
    assert windows.powershell_invocation("C:\\bin\\claude.exe", "claude -p {prompt}") == (
        "& 'C:\\bin\\claude.exe' -p $prompt"
    )
    # The per-host bit is data: Codex's unattended-run flags flow through the
    # shared builder, with the file-backed prompt kept as one PowerShell value.
    assert windows.powershell_invocation("/x/codex", CODEX.schedule_command) == (
        "& '/x/codex' exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check $prompt"
    )


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
    # PowerShell 5.1 turns native stderr into NativeCommandError. Preparation is
    # still fail-fast, but the agent call must continue long enough to log stderr
    # and preserve the native process's real exit code.
    invocation = "& 'C:\\bin\\claude.exe' -p $prompt"
    assert text.index("$ErrorActionPreference = 'Stop'") < text.index("Get-Content -Raw")
    assert text.index("$LASTEXITCODE = 1") < text.index("$ErrorActionPreference = 'Continue'")
    assert text.index("$ErrorActionPreference = 'Continue'") < text.index(invocation)
    assert text.index(invocation) < text.index("$agentExitCode = $LASTEXITCODE")
    assert "exit $agentExitCode" in text
    assert "exit $LASTEXITCODE" not in text


@pytest.mark.skipif(platform.system() != "Windows", reason="requires Windows PowerShell 5.1")
@pytest.mark.parametrize("agent_exit_code", [0, 7])
def test_wrapper_logs_native_stderr_and_propagates_exit_code(tmp_path: Path, agent_exit_code: int) -> None:
    prompt_file = tmp_path / "bridge-prompt.txt"
    log = tmp_path / "bridge.log"
    agent = tmp_path / "agent.cmd"
    wrapper = tmp_path / "memu-bridge.ps1"
    prompt_file.write_text("prompt", encoding="utf-8")
    agent.write_text(f"@echo native warning 1>&2\r\n@exit /b {agent_exit_code}\r\n", encoding="ascii")
    wrapper.write_text(
        windows.wrapper_script(str(agent), "agent {prompt}", prompt_file, log, []),
        encoding="utf-8-sig",
    )

    powershell = Path(os.environ["SYSTEMROOT"]) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    proc = subprocess.run(  # noqa: S603
        [str(powershell), "-NoProfile", "-NonInteractive", "-File", str(wrapper)],
        capture_output=True,
        check=False,
    )

    assert proc.returncode == agent_exit_code
    logged = log.read_bytes()
    assert b"native warning" in logged or "native warning".encode("utf-16-le") in logged


def test_register_script_is_canonical_and_hardened() -> None:
    script = windows.register_script("memu-bridging-claude-code", Path("C:\\w\\memu-bridge.ps1"), 60, Path("C:\\w"))
    assert "memu-bridging-claude-code" in script
    assert windows.TASK_PATH in script
    assert "-LogonType S4U" in script  # windowless + runs whether logged on or not
    assert "-StartWhenAvailable" in script  # catch up a missed run
    # Without an explicit workdir the action starts in System32 — which a
    # workspace-trust CLI (cursor-agent --trust) would then be trusting.
    assert "-WorkingDirectory 'C:\\w'" in script
    assert "New-TimeSpan -Minutes 60" in script
    assert "-Force" in script  # reinstall updates the canonical task in place
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
    assert CURSOR.task_name == "memu-bridging-cursor"
    assert HERMES.task_name == "memu-bridging-hermes"


def test_codex_template_uses_the_unattended_host_access_flags() -> None:
    assert CODEX.schedule_command == (
        "codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check {prompt}"
    )
    assert "--ephemeral" not in CODEX.schedule_command
    assert CODEX.needs_headless_auth is False
    # Session identity/self-skip is deliberately a later host survey, not part
    # of the native -> OS scheduler migration.
    assert CODEX.session_id_env == ""
    assert windows.agent_check_argv("C:\\codex.exe", CODEX.schedule_command, "ping") == [
        "C:\\codex.exe",
        "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "--skip-git-repo-check",
        "ping",
    ]


def test_hermes_template_uses_its_oneshot_flag_everywhere() -> None:
    # Hermes ships its CLI with the client; the only host-specific invocation
    # detail is its real one-shot flag. The old guide's copied `-p` never existed.
    assert HERMES.schedule_command == "hermes -z {prompt}"
    assert HERMES.schedule_prepare_session_dir is True
    assert HERMES.needs_headless_auth is False
    assert windows.agent_check_argv("C:\\hermes.exe", HERMES.schedule_command, "ping") == [
        "C:\\hermes.exe",
        "-z",
        "ping",
    ]
    assert windows.powershell_invocation("C:\\hermes.exe", HERMES.schedule_command) == ("& 'C:\\hermes.exe' -z $prompt")


def test_hermes_scheduled_prompt_bakes_in_its_session_store() -> None:
    scheduled = prompt.bridging_pipeline_prompt(
        HERMES,
        prepare_session_dir="C:/Hermes Home/state.db",
    )
    assert "memu-hermes prepare --session-dir 'C:/Hermes Home/state.db'" in scheduled
    assert "--session-dir" not in prompt.bridging_pipeline_prompt(CLAUDE)


def test_cursor_template_carries_the_trust_flag_everywhere() -> None:
    # cursor-agent refuses headless runs in an untrusted directory (field-verified:
    # "Workspace Trust Required", exit 1). Because the flag lives in the template,
    # BOTH consumers inherit it: the install-time auth probe and the scheduled
    # wrapper. Never --yolo — that is the blanket skip the guides reject.
    assert CURSOR.schedule_command == "cursor-agent --trust -p {prompt}"
    assert windows.agent_check_argv("C:\\ca.cmd", CURSOR.schedule_command, "ping") == [
        "C:\\ca.cmd",
        "--trust",
        "-p",
        "ping",
    ]
    assert windows.powershell_invocation("C:\\ca.cmd", CURSOR.schedule_command) == "& 'C:\\ca.cmd' --trust -p $prompt"


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
    for spec in (CLAUDE, CURSOR, HERMES, CODEX):
        parser = build_parser(spec)
        args = parser.parse_args(["schedule", "install"])
        assert callable(args.handler)
        assert args.action == "install"
        assert args.interval == 60
        assert parser.parse_args(["schedule", "install", "--interval", "30"]).interval == 30
        with pytest.raises(SystemExit):
            parser.parse_args(["schedule", "frobnicate"])


def test_schedule_backends_describe_existing_host_arrangements() -> None:
    assert {
        spec.host: spec.schedule_backend for spec in (CLAUDE, CURSOR, HERMES, CODEX, OPENCLAW, WORKBUDDY, COLA, GENERIC)
    } == {
        "claude-code": "os",
        "cursor": "os",
        "hermes": "os",
        "codex": "os",
        "openclaw": "native",
        "workbuddy": "native",
        "cola": "native",
        "agent": "external",
    }


@pytest.mark.parametrize("backend", ("os", "native", "external"))
def test_schedule_backend_does_not_control_verb_wiring(backend: ScheduleBackend) -> None:
    assert (
        build_parser(dataclasses.replace(CLAUDE, schedule_backend=backend)).parse_args(["schedule", "status"]).action
        == "status"
    )
    with pytest.raises(SystemExit):
        build_parser(dataclasses.replace(CLAUDE, schedule_command="", schedule_backend=backend)).parse_args([
            "schedule",
            "status",
        ])


def test_unwired_host_has_no_schedule_verb() -> None:
    # Native and external hosts never advertise a `schedule` verb, not even a
    # refusing stub. argparse rejects it as an unknown command.
    for spec in (OPENCLAW, WORKBUDDY, COLA, GENERIC):
        with pytest.raises(SystemExit):
            build_parser(spec).parse_args(["schedule", "status"])
    # ...while a wired host does have it.
    assert build_parser(CLAUDE).parse_args(["schedule", "status"]).action == "status"

    # An OS invocation remains the capability gate, independent of its label.
    unwired = dataclasses.replace(CLAUDE, schedule_command="")
    with pytest.raises(SystemExit):
        build_parser(unwired).parse_args(["schedule", "status"])


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
    assert "O''Brien" in windows.register_script("t", Path("C:\\O'Brien\\memu-bridge.ps1"), 60, Path("C:\\O'Brien"))
    assert "O''Brien" in windows.wrapper_script(
        "C:\\O'Brien\\c.exe",
        "claude -p {prompt}",
        Path("C:\\O'Brien\\p.txt"),
        Path("C:\\O'Brien\\l.log"),
        ["C:\\O'Brien"],
    )


def test_pipeline_prompt_matches_the_bridging_doc() -> None:
    # The prompt exists twice — this code builder and the doc's bridge-prompt.txt
    # block (the single-line fence the Unix registration step writes to disk) — and
    # they must stay verbatim. Lock it here: drift fails a test, not silently later.
    from importlib.resources import files

    doc = (files("memu.hosts.claude_code") / "BRIDGING_TASK.md").read_text(encoding="utf-8")
    doc_prompt = next(
        line.strip() for line in doc.splitlines() if line.strip().startswith("Run the memU bridging pipeline.")
    )
    assert doc_prompt == prompt.bridging_pipeline_prompt(CLAUDE)


def test_codex_pipeline_prompt_matches_the_bridging_doc() -> None:
    from importlib.resources import files

    doc = (files("memu.hosts.codex") / "BRIDGING_TASK.md").read_text(encoding="utf-8")
    doc_prompt = next(
        line.strip() for line in doc.splitlines() if line.strip().startswith("Run the memU bridging pipeline.")
    )
    assert doc_prompt == prompt.bridging_pipeline_prompt(CODEX)


def test_cursor_pipeline_prompt_matches_the_bridging_doc() -> None:
    # Wiring cursor makes bridging_pipeline_prompt(CURSOR) live on Windows; lock its
    # guide's bridge-prompt.txt block to the canon the same way claude's is locked.
    from importlib.resources import files

    doc = (files("memu.hosts.cursor") / "BRIDGING_TASK.md").read_text(encoding="utf-8")
    doc_prompt = next(
        line.strip() for line in doc.splitlines() if line.strip().startswith("Run the memU bridging pipeline.")
    )
    assert doc_prompt == prompt.bridging_pipeline_prompt(CURSOR)


def test_hermes_pipeline_prompt_matches_the_bridging_doc() -> None:
    from importlib.resources import files

    doc = (files("memu.hosts.hermes") / "BRIDGING_TASK.md").read_text(encoding="utf-8")
    doc_prompt = next(
        line.strip() for line in doc.splitlines() if line.strip().startswith("Run the memU bridging pipeline.")
    )
    assert doc_prompt == prompt.bridging_pipeline_prompt(HERMES)


@pytest.mark.parametrize("pkg", ["claude_code", "codex", "cursor", "hermes", "generic"])
def test_bridging_doc_cron_entries_stay_short(pkg: str) -> None:
    # The bug class behind memU#591: an inlined pipeline prompt pushed the guide's
    # crontab entry past cron's ~1KB line buffer, so every tick died mid-quote
    # before the agent binary ever started. The prompt-lock tests above catch
    # content drift but not re-inlining — this gate does. Every cron entry a
    # Unix guide tells the agent to write must stay far below the buffer.
    from importlib.resources import files

    doc = (files(f"memu.hosts.{pkg}") / "BRIDGING_TASK.md").read_text(encoding="utf-8")
    cron_entries = [line for line in doc.splitlines() if line.lstrip().startswith("0 * * * * ")]
    assert cron_entries, f"{pkg} guide lost its cron entry example"
    for line in cron_entries:
        assert len(line) < 512, f"{pkg} cron entry is {len(line)} chars — cron truncates around 1KB: {line[:80]!r}"


def test_codex_guide_migrates_native_task_before_os_registration() -> None:
    from importlib.resources import files

    doc = (files("memu.hosts.codex") / "BRIDGING_TASK.md").read_text(encoding="utf-8")
    migration = doc.index("Legacy native-task migration")
    unix_registration = doc.index("0 * * * * $HOME/.memu/hosts/codex/bridge.sh")
    windows_registration = doc.index("memu-codex schedule install")
    assert migration < unix_registration
    assert migration < windows_registration
    assert "MEMU_BRIDGING_TASK_ID=memu:bridging:codex:v1" in doc
    assert all(
        signature in doc
        for signature in (
            "Run the memU bridging pipeline",
            "memu-codex prepare",
            "memu-codex commit",
            "~/.memu/hosts/codex/jobs",
        )
    )
    assert "Migrate it automatically" in doc
    assert "needs no separate confirmation" in doc
    assert "obtain explicit confirmation" not in doc
    assert "If listing, deletion, classification, or verification fails, stop" in doc
    assert "Do not create the OS task" in doc


def test_hermes_guide_migrates_native_job_before_os_registration() -> None:
    from importlib.resources import files

    doc = (files("memu.hosts.hermes") / "BRIDGING_TASK.md").read_text(encoding="utf-8")
    migration = doc.index("hermes cron list --all")
    unix_registration = doc.index("0 * * * * $HOME/.memu/hosts/hermes/bridge.sh")
    windows_registration = doc.index("memu-hermes schedule install")
    assert migration < unix_registration
    assert migration < windows_registration
    assert "hermes cron remove <job-id>" in doc
    assert "If listing or removal fails, stop" in doc


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
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A pass is necessary but not sufficient: the S4U task won't see a session-only
    # $env: token, so even the passing path must tell the user to persist it (#538 B).
    monkeypatch.setattr(windows, "_authenticates", lambda spec, path, workdir: (True, ""))
    assert windows._auth_gate(CLAUDE, "C:\\claude.exe", tmp_path) == 0
    assert "PERSISTENT" in capsys.readouterr().err


def test_auth_gate_aborts_when_unauthenticated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(windows, "_authenticates", lambda spec, path, workdir: (False, "Not logged in"))
    assert windows._auth_gate(CLAUDE, "C:\\claude.exe", tmp_path) == 1
    err = capsys.readouterr().err
    assert "setup-token" in err and "PERSISTENT" in err


def test_auth_gate_failure_speaks_the_hosts_own_remedy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The remedy is HostSpec.auth_hint data: a cursor failure must point at the
    # IDE session / `cursor-agent login`, never at claude's `setup-token`.
    monkeypatch.setattr(windows, "_authenticates", lambda spec, path, workdir: (False, "Not logged in"))
    assert windows._auth_gate(CURSOR, "C:\\ca.cmd", tmp_path) == 1
    err = capsys.readouterr().err
    assert "cursor-agent login" in err
    assert "setup-token" not in err


def test_symptom_a_message_carries_concrete_install_commands(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # When claude isn't on PATH the refusal must be copy-pasteable — the host's own
    # install commands (memU#538 Symptom A), not vague "winget/npm" prose.
    monkeypatch.setattr(windows.platform, "system", lambda: "Windows")
    monkeypatch.setattr(windows, "_resolve_agent", lambda spec: None)
    layout = Layout.default(host=CLAUDE.host, base=tmp_path)
    assert windows.install(CLAUDE, layout) == 1
    err = capsys.readouterr().err
    assert "winget install Anthropic.ClaudeCode" in err
    assert "Symptom A" in err
