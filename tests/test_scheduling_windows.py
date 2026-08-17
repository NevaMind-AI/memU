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

SPECS = (CLAUDE, CURSOR, HERMES, CODEX, OPENCLAW, WORKBUDDY, COLA, GENERIC)

EXPECTED_TASK_NAMES = {
    "claude-code": ("memu-bridging-claude-code", ("memu-remember-claude-code",)),
    "cursor": ("memu-bridging-cursor", ()),
    "hermes": ("memu-bridging-hermes", ()),
    "codex": ("memu-bridging-codex", ("memu-remember", "memu-bridging")),
    "openclaw": ("memu-bridging-openclaw", ("memu-remember", "memu-bridging")),
    "workbuddy": ("memu-bridging-workbuddy", ()),
    "cola": ("memu-bridging-cola", ("memu-bridging", "memU 记忆桥接")),
    "agent": ("memu-bridging-agent", ()),
}


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
    script = windows.register_script("memu-bridging-claude-code", Path("C:\\w\\memu-bridge.ps1"), 60, Path("C:\\w"))
    assert "memu-bridging-claude-code" in script
    assert windows.TASK_PATH in script
    assert "-LogonType S4U" in script  # windowless + runs whether logged on or not
    assert "-StartWhenAvailable" in script  # catch up a missed run
    # Without an explicit workdir the action starts in System32 — which a
    # workspace-trust CLI (cursor-agent --trust) would then be trusting.
    assert "-WorkingDirectory 'C:\\w'" in script
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


def test_task_names_are_declared_once_per_host() -> None:
    assert {spec.host: (spec.task_name, spec.former_task_names) for spec in SPECS} == EXPECTED_TASK_NAMES
    for spec in SPECS:
        assert spec.all_task_names == (spec.task_name, *spec.former_task_names)
        assert spec.task_doc_name == f"create-{spec.task_name}-task"
        assert len(set(spec.all_task_names)) == len(spec.all_task_names)


def test_host_spec_rejects_invalid_task_names() -> None:
    with pytest.raises(ValueError, match="invalid task_name"):
        dataclasses.replace(CLAUDE, task_name="memu remember claude")
    with pytest.raises(ValueError, match="must not also appear"):
        dataclasses.replace(CLAUDE, former_task_names=(CLAUDE.task_name,))
    with pytest.raises(ValueError, match="duplicates"):
        dataclasses.replace(CLAUDE, former_task_names=("old", "old"))


def test_claude_task_guide_uses_host_spec_tokens() -> None:
    from importlib.resources import files

    task_source = (files("memu.hosts.claude_code") / "BRIDGING_TASK.md").read_text(encoding="utf-8")
    install_source = (files("memu.hosts.claude_code") / "INSTALL.md").read_text(encoding="utf-8")
    task_doc = CLAUDE.render_doc(task_source)
    install_doc = CLAUDE.render_doc(install_source)

    assert f"name: {CLAUDE.task_doc_name}" in task_doc
    assert CLAUDE.task_name in task_doc and CLAUDE.task_name in install_doc
    assert all(name in task_doc and name in install_doc for name in CLAUDE.former_task_names)
    assert windows.TASK_PATH not in task_doc and windows.TASK_PATH not in install_doc
    assert "{{" not in task_doc and "{{" not in install_doc


def test_legacy_task_script_is_limited_to_the_given_task() -> None:
    script = windows.unregister_if_present_script("memu-remember-claude-code")
    assert "memu-remember-claude-code" in script
    assert "memu-bridging-claude-code" not in script
    assert windows.TASK_PATH in script
    assert "Get-ScheduledTask" in script
    assert "Unregister-ScheduledTask" in script


def test_claude_install_migrates_the_legacy_task_before_registering(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    scripts: list[str] = []
    monkeypatch.setattr(windows.platform, "system", lambda: "Windows")
    monkeypatch.setattr(windows, "_resolve_agent", lambda spec: "C:\\bin\\claude.exe")
    monkeypatch.setattr(windows, "_auth_gate", lambda spec, path, workdir: 0)
    monkeypatch.setattr(windows.shutil, "which", lambda binary: None)

    def run(script: str) -> subprocess.CompletedProcess[str]:
        scripts.append(script)
        return subprocess.CompletedProcess([], 0, "", "")

    monkeypatch.setattr(windows, "_run_powershell", run)

    assert windows.install(CLAUDE, Layout.default(host=CLAUDE.host, base=tmp_path)) == 0
    assert "memu-remember-claude-code" in scripts[0]
    assert "memu-bridging-claude-code" in scripts[1]
    assert len(scripts) == 2


@pytest.mark.parametrize(
    ("canonical", "legacy", "expected"),
    [
        (False, False, "not registered"),
        (False, True, "former registration"),
        (True, False, "current"),
        (True, True, "duplicate registrations"),
    ],
)
def test_claude_status_reports_migration_states(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    canonical: bool,
    legacy: bool,
    expected: str,
) -> None:
    monkeypatch.setattr(windows.platform, "system", lambda: "Windows")

    def run(script: str) -> subprocess.CompletedProcess[str]:
        registered = "memu-bridging-claude-code" in script and canonical
        legacy_registered = "memu-remember-claude-code" in script and legacy
        return subprocess.CompletedProcess([], 0 if registered or legacy_registered else 1, "current", "")

    monkeypatch.setattr(windows, "_run_powershell", run)
    assert windows.status(CLAUDE, Layout.default(host=CLAUDE.host, base=tmp_path)) == 0
    assert expected in capsys.readouterr().out


@pytest.mark.parametrize(
    ("canonical", "legacy"),
    [(False, False), (False, True), (True, True)],
)
def test_claude_verify_rejects_missing_or_legacy_registration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    canonical: bool,
    legacy: bool,
) -> None:
    monkeypatch.setattr(windows.platform, "system", lambda: "Windows")

    def run(script: str) -> subprocess.CompletedProcess[str]:
        registered = "memu-bridging-claude-code" in script and canonical
        legacy_registered = "memu-remember-claude-code" in script and legacy
        return subprocess.CompletedProcess([], 0 if registered or legacy_registered else 1, "", "")

    monkeypatch.setattr(windows, "_run_powershell", run)
    assert windows.verify(CLAUDE, Layout.default(host=CLAUDE.host, base=tmp_path)) == 1
    assert "schedule install" in capsys.readouterr().err


def test_claude_uninstall_removes_only_known_identities(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    scripts: list[str] = []
    monkeypatch.setattr(windows.platform, "system", lambda: "Windows")

    def run(script: str) -> subprocess.CompletedProcess[str]:
        scripts.append(script)
        return subprocess.CompletedProcess([], 0, "", "")

    monkeypatch.setattr(windows, "_run_powershell", run)

    assert windows.uninstall(CLAUDE, Layout.default(host=CLAUDE.host, base=tmp_path)) == 0
    assert len(scripts) == 2
    assert "memu-remember-claude-code" in scripts[0]
    assert "memu-bridging-claude-code" in scripts[1]


def test_windows_lifecycle_checks_every_former_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    spec = dataclasses.replace(CLAUDE, former_task_names=("memu-old-one", "memu-old-two"))
    scripts: list[str] = []
    monkeypatch.setattr(windows.platform, "system", lambda: "Windows")

    def run(script: str) -> subprocess.CompletedProcess[str]:
        scripts.append(script)
        registered = any(name in script for name in spec.former_task_names)
        return subprocess.CompletedProcess([], 0 if registered else 1, "", "")

    monkeypatch.setattr(windows, "_run_powershell", run)

    assert windows.status(spec, Layout.default(host=spec.host, base=tmp_path)) == 0
    output = capsys.readouterr().out
    assert all(name in output for name in spec.former_task_names)
    assert all(any(name in script for script in scripts) for name in spec.former_task_names)

    scripts.clear()
    assert windows.uninstall(spec, Layout.default(host=spec.host, base=tmp_path)) == 0
    assert len(scripts) == len(spec.all_task_names)
    assert all(any(name in script for script in scripts) for name in spec.all_task_names)


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
    for spec in (CLAUDE, CURSOR, HERMES):
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
        "codex": "native",
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
    for spec in (CODEX, OPENCLAW, WORKBUDDY, COLA, GENERIC):
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


@pytest.mark.parametrize("pkg", ["claude_code", "cursor", "hermes", "generic"])
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


@pytest.mark.parametrize(
    ("pkg", "binary", "identity"),
    [
        ("claude_code", "memu-claude-code", r"hosts/claude-code/bridge\.sh|memU bridging pipeline"),
        ("cursor", "memu-cursor", r"hosts/cursor/bridge\.sh|memU bridging pipeline"),
        ("hermes", "memu-hermes", r"hosts/hermes/bridge\.sh|memU bridging pipeline"),
        ("generic", "memu-agent", r"hosts/agent/bridge\.sh|memU bridging pipeline"),
        ("codex", "memu-codex", "load-bearing deletion identity"),
        ("openclaw", "memu-openclaw", ".cron_job.openclaw.json"),
        ("workbuddy", "memu-workbuddy", "WorkBuddy's automation list"),
        ("cola", "memu-cola", "{{all_task_names}}"),
    ],
)
def test_install_refreshes_existing_bridge_before_registration(pkg: str, binary: str, identity: str) -> None:
    """An upgrade removes only the old registration before applying today's task guide (#640)."""
    from importlib.resources import files

    doc = (files(f"memu.hosts.{pkg}") / "INSTALL.md").read_text(encoding="utf-8")
    normalized = " ".join(doc.replace("**", "").split())
    refresh = normalized.index("Refresh an existing bridging registration before continuing.")
    registration = normalized.index(f"{binary} docs task", refresh)
    refresh_step = normalized[refresh:registration]

    assert identity in refresh_step
    assert " only " in refresh_step and ("remove " in refresh_step or "delete " in refresh_step)
    assert "verify" in refresh_step.lower()
    assert "normal first-install case" in refresh_step
    assert "unless the user requested a change" in refresh_step
    assert "UNINSTALL.md" not in refresh_step


def test_cursor_uninstall_documents_windows_schedule_removal() -> None:
    from importlib.resources import files

    doc = (files("memu.hosts.cursor") / "UNINSTALL.md").read_text(encoding="utf-8")
    assert "memu-cursor schedule uninstall" in doc
    assert "memu-cursor schedule status" in doc
    assert "Get-ScheduledTask -TaskPath" not in doc


def test_cola_task_recreates_existing_bridge() -> None:
    from importlib.resources import files

    doc = (files("memu.hosts.cola") / "BRIDGING_TASK.md").read_text(encoding="utf-8")
    normalized = " ".join(doc.split())
    existing = normalized.index("If any task whose name is in {{all_task_names}} already exists")
    create = normalized.index("Set its prompt")
    refresh = normalized[existing:create]

    assert "remove only that task" in refresh
    assert "verify it no longer appears" in refresh
    assert "update it rather than" not in normalized


def test_openclaw_task_recreates_confirmed_bridge() -> None:
    from importlib.resources import files

    doc = (files("memu.hosts.openclaw") / "BRIDGING_TASK.md").read_text(encoding="utf-8")
    normalized = " ".join(doc.split())
    candidate = normalized.index("Exactly one candidate and zero unresolved near matches")
    create = normalized.index("## Step 2 — create and register the cron job")
    refresh = normalized[candidate:create]

    assert "delete only that exact job ID" in refresh
    assert "verify it no longer appears" in refresh
    assert "reuse and preserve" not in normalized
    assert "in-place patch" not in normalized
    assert "selected, updated, or created" not in normalized


@pytest.mark.parametrize(
    ("pkg", "task_doc_signals", "uninstall_signals"),
    [
        (
            "claude_code",
            ("$HOME/.memu/hosts/claude-code/bridge.sh", "{{task_name}}"),
            ("hosts/claude-code/bridge\\.sh|memU bridging pipeline", "schedule uninstall"),
        ),
        (
            "cursor",
            ("$HOME/.memu/hosts/cursor/bridge.sh", "{{task_name}}"),
            ("hosts/cursor/bridge\\.sh|memU bridging pipeline", "schedule uninstall"),
        ),
        (
            "hermes",
            ("$HOME/.memu/hosts/hermes/bridge.sh", "{{task_name}}", "hermes cron remove <job-id>"),
            ("hosts/hermes/bridge\\.sh|memU bridging pipeline", "hermes cron remove <job-id>"),
        ),
        (
            "generic",
            (
                "$HOME/.memu/hosts/agent/bridge.sh",
                "memu-agent prepare --session-dir <SESSION_DIR>",
                "memu-agent commit",
            ),
            ("hosts/agent/bridge\\.sh|memU bridging pipeline", "memu-agent prepare --session-dir …"),
        ),
    ],
)
def test_os_scheduler_identity_docs_stay_aligned(
    pkg: str, task_doc_signals: tuple[str, ...], uninstall_signals: tuple[str, ...]
) -> None:
    from importlib.resources import files

    package = files(f"memu.hosts.{pkg}")
    task_doc = (package / "BRIDGING_TASK.md").read_text(encoding="utf-8")
    uninstall_doc = (package / "UNINSTALL.md").read_text(encoding="utf-8")

    for signal in task_doc_signals:
        assert signal in task_doc
    for signal in uninstall_signals:
        assert signal in uninstall_doc


def test_native_scheduler_identity_docs_stay_explicit() -> None:
    from importlib.resources import files

    cola_source = (files("memu.hosts.cola") / "BRIDGING_TASK.md").read_text(encoding="utf-8")
    cola = " ".join(COLA.render_doc(cola_source).split())
    assert COLA.task_name in cola
    assert all(name in cola for name in COLA.former_task_names)
    assert "desktop:local" in cola

    codex_source = (files("memu.hosts.codex") / "BRIDGING_TASK.md").read_text(encoding="utf-8")
    codex_uninstall_source = (files("memu.hosts.codex") / "UNINSTALL.md").read_text(encoding="utf-8")
    codex = " ".join(CODEX.render_doc(codex_source).split())
    codex_uninstall = " ".join(CODEX.render_doc(codex_uninstall_source).split())
    assert f"named `{CODEX.task_name}`" in codex
    assert "name is only a hint" in codex_uninstall
    assert "prepare / self-evolve / commit" in codex_uninstall

    openclaw_source = (files("memu.hosts.openclaw") / "BRIDGING_TASK.md").read_text(encoding="utf-8")
    openclaw_uninstall_source = (files("memu.hosts.openclaw") / "UNINSTALL.md").read_text(encoding="utf-8")
    openclaw = " ".join(OPENCLAW.render_doc(openclaw_source).split())
    openclaw_uninstall = " ".join(OPENCLAW.render_doc(openclaw_uninstall_source).split())
    assert f"named `{OPENCLAW.task_name}`" in openclaw
    assert "registered ID" in openclaw_uninstall
    assert "use that exact identity" in openclaw_uninstall

    workbuddy_source = (files("memu.hosts.workbuddy") / "BRIDGING_TASK.md").read_text(encoding="utf-8")
    workbuddy_uninstall_source = (files("memu.hosts.workbuddy") / "UNINSTALL.md").read_text(encoding="utf-8")
    workbuddy = " ".join(WORKBUDDY.render_doc(workbuddy_source).split())
    workbuddy_uninstall = " ".join(WORKBUDDY.render_doc(workbuddy_uninstall_source).split())
    assert WORKBUDDY.task_name in workbuddy
    assert "no separate name field" in workbuddy
    assert "automation ID plus complete pipeline" in workbuddy
    assert "exact automation ID" in workbuddy_uninstall
    assert "name alone is never enough" in workbuddy_uninstall

    generic_source = (files("memu.hosts.generic") / "BRIDGING_TASK.md").read_text(encoding="utf-8")
    generic_uninstall_source = (files("memu.hosts.generic") / "UNINSTALL.md").read_text(encoding="utf-8")
    generic = GENERIC.render_doc(generic_source)
    generic_uninstall = GENERIC.render_doc(generic_uninstall_source)
    assert f"use `{GENERIC.task_name}`" in generic
    assert "replace the final `agent`" in generic
    assert "matching each" in generic and "--base-dir ~/.memu/hosts/<name>" in generic
    assert "pipeline prompt remains the load-bearing" in generic
    assert "confirm the pipeline prompt" in generic_uninstall


def test_claude_preflight_never_treats_task_presence_as_current() -> None:
    from importlib.resources import files

    doc = (files("memu.hosts.claude_code") / "INSTALL.md").read_text(encoding="utf-8")
    assert "there is nothing to install" not in doc
    assert "Part 2 always runs once its prerequisites pass" in doc


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
