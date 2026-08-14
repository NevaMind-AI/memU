r"""Register the memU bridging task with Windows Task Scheduler.

Unix hosts schedule bridging by pasting the pipeline prompt into a crontab or a
launchd plist (see each host's ``BRIDGING_TASK.md``). Windows can't take that
path — Task Scheduler's ``schtasks /TR`` re-parses the ~1000-character quoted
prompt and dies on the spaces (memU#539), and a bare scheduled process can't find
a desktop-only ``claude`` (memU#538). This backend sidesteps both: it writes the
prompt to a file and a small PowerShell wrapper that reads it, then registers a
Task Scheduler entry that runs *only* the wrapper, under a canonical task name.

Prior art: **jshchnz/claude-code-scheduler** — the established (500+ star) Claude
Code scheduler, with per-OS backends over schtasks/launchd/cron and every task
namespaced under a scheduler folder (``\ClaudeScheduler\<id>``; ours is the same
shape, ``\memU\<name>``, so uninstall is deterministic). We diverge for the
bridging case: ``Register-ScheduledTask`` under an S4U principal, so the run is
windowless and works while logged out, plus the prompt-file indirection below
because the pipeline prompt is too long to sit on the command line.

Windows-only: every entry point raises on other platforms. Nothing here touches
the cron or launchd code paths, so their long-standing behavior is unchanged.
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from memu.hosts.bridging.self_sessions import BRIDGING_RUN_ENV
from memu.hosts.scheduling.prompt import bridging_pipeline_prompt

if TYPE_CHECKING:
    from memu.hosts.bridging import Layout
    from memu.hosts.host_cli import HostSpec

# Task Scheduler folder that namespaces every memU task, so `\memU\<name>` never
# collides with an unrelated task and a whole-folder query lists only ours.
TASK_PATH = "\\memU\\"
DEFAULT_INTERVAL_MINUTES = 60

WRAPPER_NAME = "memu-bridge.ps1"
PROMPT_NAME = "bridge-prompt.txt"
LOG_NAME = "bridge.log"


# ---------------------------------------------------------------------------
# Pure builders — no I/O, no platform gate; unit-tested on any OS.
# ---------------------------------------------------------------------------


def _invocation_args(schedule_command: str) -> list[str]:
    """The agent's arguments after the binary, with ``{prompt}`` still a token.

    ``schedule_command`` is ``claude -p {prompt}`` / ``codex exec {prompt}``; the
    first token is the binary (resolved separately to an absolute path) and the
    ``{prompt}`` placeholder must stand alone so it maps cleanly to one argument.
    """
    tokens = schedule_command.split()
    if not tokens:
        msg = "schedule_command is empty"
        raise ValueError(msg)
    return tokens[1:]


def _ps_quote(value: str) -> str:
    """``value`` as a PowerShell single-quoted literal, doubling any ``'``.

    Every value the builders embed — paths, the task name, the wrapper argument —
    goes through here, so a username or directory holding an apostrophe
    (``C:\\Users\\O'Brien``) can't terminate the string early and break the script.
    Symmetric with the CJK + BOM handling in ``install``.
    """
    return "'" + value.replace("'", "''") + "'"


def powershell_invocation(agent_path: str, schedule_command: str, *, prompt_stdin: bool = False) -> str:
    """The wrapper's agent call, e.g. ``& 'C:\\...\\claude.exe' -p $prompt``.

    ``$prompt`` is the wrapper variable holding the prompt file's contents, so the
    long text is passed as one argument by PowerShell and never touches a shell
    that would split it on spaces — the whole point of the file indirection.
    """
    prompt_token = "-" if prompt_stdin else "$prompt"
    rest = [prompt_token if t == "{prompt}" else t for t in _invocation_args(schedule_command)]
    invocation = " ".join([f"& {_ps_quote(agent_path)}", *rest])
    return f"$prompt | {invocation}" if prompt_stdin else invocation


def agent_check_argv(agent_path: str, schedule_command: str, prompt: str) -> list[str]:
    """The argv for a headless auth probe, e.g. ``[claude, -p, ping]`` (memU#538)."""
    rest = [prompt if t == "{prompt}" else t for t in _invocation_args(schedule_command)]
    return [agent_path, *rest]


def wrapper_script(
    agent_path: str,
    schedule_command: str,
    prompt_file: Path,
    log_file: Path,
    path_dirs: list[str],
    *,
    prompt_stdin: bool = False,
) -> str:
    """The PowerShell wrapper the scheduled task runs.

    It re-establishes ``PATH`` (Task Scheduler does not inherit the interactive
    shell's), reads the prompt from a file, and runs the agent. Absolute paths are
    baked in at install time — the #530 "the scheduler's PATH is not your shell's"
    capture, ported to Windows.

    Preparation stays fail-fast, but the native agent call must run under
    ``Continue``. Windows PowerShell 5.1 promotes any native stderr line to a
    ``NativeCommandError``; under ``Stop`` that aborts the wrapper before output is
    logged or ``LASTEXITCODE`` is propagated. The default exit code protects the
    command-not-found case, while a real native launch overwrites it.
    """
    path_prefix = ";".join(path_dirs)
    return "\n".join([
        "# memU bridging wrapper (generated by `schedule install`; do not edit -",
        "# re-run install to regenerate). Prior art: jshchnz/claude-code-scheduler.",
        "$ErrorActionPreference = 'Stop'",
        # Marks the run as the scheduled one, so `prepare` may skip its own session
        # (#606). It travels in the environment rather than the prompt so a person
        # running prepare by hand never trips it, and so an agent that changes
        # directory first cannot lose it.
        f"$env:{BRIDGING_RUN_ENV} = '1'",
        f"$env:Path = {_ps_quote(path_prefix + ';')} + $env:Path",
        f"$prompt = Get-Content -Raw -Encoding UTF8 -LiteralPath {_ps_quote(str(prompt_file))}",
        "$LASTEXITCODE = 1",
        "$ErrorActionPreference = 'Continue'",
        f"{powershell_invocation(agent_path, schedule_command, prompt_stdin=prompt_stdin)} "
        f"*>> {_ps_quote(str(log_file))}",
        "$agentExitCode = $LASTEXITCODE",
        "$ErrorActionPreference = 'Stop'",
        "exit $agentExitCode",
        "",
    ])


def register_script(task_name: str, wrapper_path: Path, interval_minutes: int, workdir: Path) -> str:
    """PowerShell that registers the task.

    - ``-LogonType S4U``: runs whether or not the user is logged on, with no stored
      password, and — running in session 0 — windowless, so no console flashes each
      run (a schtasks-based approach needs a hidden-VBS or ``-WindowStyle Hidden``
      shim for this; the principal gives it to us for free).
    - ``-RunLevel Limited``: bridging is not an admin job; elevating could read a
      different profile's credentials.
    - ``-StartWhenAvailable``: catch up a run missed while the machine was off.
    - ``-WorkingDirectory``: without it Task Scheduler starts the action in
      ``System32``. Any agent CLI with a workspace-trust gate (``cursor-agent
      --trust``) would then be granting trust to ``System32``; the host's own
      working tree is the deliberate workdir for every host.
    - ``-RepetitionInterval`` off a ``-Once`` trigger, with an explicit
      ``-RepetitionDuration``. Without one, Win10/11 default the repetition to ~1 day
      and the task silently stops after a day (exactly the #539 "installed but quietly
      dead" failure). ``[TimeSpan]::MaxValue`` is rejected on real Win11 ("value out of
      range" in the task XML — verified), so this uses ~10 years: in range, and
      effectively forever for a bridging task.
    """
    arg = f'-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{wrapper_path}"'
    return "\n".join([
        f"$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument {_ps_quote(arg)} "
        f"-WorkingDirectory {_ps_quote(str(workdir))}",
        "$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date "
        f"-RepetitionInterval (New-TimeSpan -Minutes {interval_minutes}) -RepetitionDuration (New-TimeSpan -Days 3650)",
        "$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited",
        "$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew "
        "-AllowStartIfOnBatteries -DontStopIfGoingOnBatteries",
        f"Register-ScheduledTask -TaskName {_ps_quote(task_name)} -TaskPath {_ps_quote(TASK_PATH)} "
        "-Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null",
    ])


def unregister_script(task_name: str) -> str:
    return f"Unregister-ScheduledTask -TaskName {_ps_quote(task_name)} -TaskPath {_ps_quote(TASK_PATH)} -Confirm:$false"


def status_script(task_name: str) -> str:
    return (
        f"Get-ScheduledTaskInfo -TaskName {_ps_quote(task_name)} -TaskPath {_ps_quote(TASK_PATH)} | "
        "Format-List TaskName, LastRunTime, LastTaskResult, NextRunTime"
    )


# ---------------------------------------------------------------------------
# Execution — Windows-only.
# ---------------------------------------------------------------------------


def _require_windows() -> None:
    if platform.system() != "Windows":
        msg = "the Windows Task Scheduler backend is only usable on Windows"
        raise RuntimeError(msg)


def _run_powershell(
    script: str,
    *,
    cwd: Path | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    # powershell.exe is a fixed Windows system binary (resolved from System32) and
    # `script` is generated here, never user input — the bandit process checks don't apply.
    argv = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script]
    # encoding/errors pinned: PowerShell's own output follows the console code page
    # (gbk on zh-CN Windows), but text piped through it (e.g. an agent CLI's UTF-8
    # reply) is not re-encoded, so a locale-default decode can crash on it (memU#512).
    return subprocess.run(  # noqa: S603
        argv,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd,
        timeout=timeout,
    )


def _agent_binary(spec: HostSpec) -> str:
    return spec.schedule_command.split()[0]


def _resolve_agent(spec: HostSpec) -> str | None:
    """The file-backed command Windows PowerShell itself resolves for the agent.

    ``shutil.which`` does not implement PowerShell's command precedence: on the
    same PATH it can choose an ``.exe`` that PowerShell would put behind a
    ``.ps1`` shim. The scheduled wrapper is PowerShell, so resolve with
    ``Get-Command`` and embed exactly what the user sees there. Aliases and
    functions are deliberately rejected because an S4U process cannot inherit
    definitions from the installer's interactive session.
    """
    binary = _agent_binary(spec)
    script = "\n".join([
        f"$command = Get-Command -Name {_ps_quote(binary)} -ErrorAction SilentlyContinue",
        "if ($null -eq $command) { exit 1 }",
        "if ($command.CommandType -notin @('Application', 'ExternalScript')) { exit 2 }",
        "[Console]::Out.Write($command.Source)",
    ])
    proc = _run_powershell(script)
    source = proc.stdout.strip()
    return source if proc.returncode == 0 and source else None


def _run_agent(
    agent_path: str,
    args: list[str],
    workdir: Path,
    *,
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    """Run the exact resolved command under the same PowerShell as the wrapper."""
    invocation = " ".join(["&", _ps_quote(agent_path), *(_ps_quote(arg) for arg in args)])
    script = "\n".join([
        "$ErrorActionPreference = 'Continue'",
        "$LASTEXITCODE = 1",
        invocation,
        "$agentExitCode = $LASTEXITCODE",
        "exit $agentExitCode",
    ])
    return _run_powershell(script, cwd=workdir, timeout=timeout)


def _launches(agent_path: str, workdir: Path) -> tuple[bool, str]:
    """Can PowerShell execute the exact selected command at all?"""
    try:
        proc = _run_agent(agent_path, ["--version"], workdir, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    return proc.returncode == 0, (proc.stderr or proc.stdout).strip()


def _launch_gate(spec: HostSpec, agent_path: str, workdir: Path) -> int:
    ok, detail = _launches(agent_path, workdir)
    if ok:
        print(f"  PowerShell selected and launched: {agent_path}")
        return 0
    hint = spec.install_hint or f"  Install {spec.display} so `{_agent_binary(spec)}` works in PowerShell."
    print(
        f"error: PowerShell resolves `{_agent_binary(spec)}` to {agent_path}, but that exact command "
        f"failed `{_agent_binary(spec)} --version` ({detail or 'no output'}).\n"
        "  Fix the command in this PowerShell environment, then re-run schedule install.\n"
        f"{hint}",
        file=sys.stderr,
    )
    return 1


def _authenticates(spec: HostSpec, agent_path: str, workdir: Path) -> tuple[bool, str]:
    """Does a cold headless run authenticate? (memU#538 Symptom B.)

    Runs the host's own invocation with a trivial prompt, in ``workdir`` — the same
    directory the scheduled task will run in, so a workspace-trust flag in the
    template (``cursor-agent --trust``) grants trust to the host's working tree,
    never to wherever the user happened to run ``schedule install``. Exit 0 means
    the CLI has a usable headless credential; the failure to catch is "Not logged
    in · Please run /login" (exit 1), where a desktop login exists but the CLI
    cannot see it.
    """
    argv = agent_check_argv(agent_path, spec.schedule_command, "ping")
    try:
        proc = _run_agent(agent_path, argv[1:], workdir, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    return proc.returncode == 0, (proc.stderr or proc.stdout).strip()


def _paths(layout: Layout) -> tuple[Path, Path, Path, Path]:
    base = layout.base
    return base / WRAPPER_NAME, base / PROMPT_NAME, base / LOG_NAME, base / f".schedule.{layout.host}.json"


def _auth_gate(spec: HostSpec, agent_path: str, workdir: Path) -> int:
    """Run the headless-auth check for hosts that need it; 0 = pass, 1 = abort.

    Caveat this can't fully close: the probe runs in *this* process's environment,
    but the scheduled task runs S4U in session 0 and inherits only *persistent*
    user/machine env + the user profile — not a session-only ``$env:`` export. So a
    pass is necessary but not sufficient, and we say so rather than imply a green gate.
    The remedy is host data (``HostSpec.auth_hint``), not hardcoded here — claude's
    fix would be wrong advice for a cursor failure.
    """
    if not spec.needs_headless_auth:
        return 0
    ok, detail = _authenticates(spec, agent_path, workdir)
    if not ok:
        hint = spec.auth_hint or "    give the CLI a persistent headless credential per its own docs"
        print(
            f"error: `{_agent_binary(spec)}` resolves but cannot authenticate headless "
            f"({detail or 'no output'}).\n"
            "  The scheduled run has no browser and cannot reuse a desktop-app login. "
            "Give the CLI its own PERSISTENT headless credential:\n"
            f"{hint}\n"
            f"  then re-run. (memU#538 Symptom B.)",
            file=sys.stderr,
        )
        return 1
    print(
        f"  note: `{_agent_binary(spec)}` authenticated in THIS shell. The task runs headless "
        "(S4U / session 0) and sees only PERSISTENT credentials — a session-only `$env:` export "
        "will NOT reach it. If the credential is session-only, persist it before relying on "
        "the schedule.",
        file=sys.stderr,
    )
    return 0


def install(spec: HostSpec, layout: Layout, *, interval_minutes: int = DEFAULT_INTERVAL_MINUTES) -> int:
    """Register or replace the bridging task, gating on a usable CLI first."""
    _require_windows()
    if interval_minutes < 1:
        print(f"error: --interval must be a positive number of minutes (got {interval_minutes})", file=sys.stderr)
        return 2
    agent_path = _resolve_agent(spec)
    if agent_path is None:
        hint = spec.install_hint or f"  Install {spec.display} so its bundled `{_agent_binary(spec)}` CLI is on PATH."
        print(
            f"error: `{_agent_binary(spec)}` is not a file-backed PowerShell command — "
            f"{spec.display}'s scheduled run needs one a bare process can launch (memU#538 Symptom A).\n"
            f"{hint}\n"
            f"  Then re-run `{spec.binary} schedule install`.",
            file=sys.stderr,
        )
        return 1
    layout.base.mkdir(parents=True, exist_ok=True)
    if (rc := _launch_gate(spec, agent_path, layout.base)) != 0:
        return rc
    if (rc := _auth_gate(spec, agent_path, layout.base)) != 0:
        return rc

    wrapper, prompt_file, log_file, registry = _paths(layout)
    prepare_session_dir = spec.session_dir if spec.schedule_prepare_session_dir else None
    prompt_file.write_text(
        bridging_pipeline_prompt(spec, prepare_session_dir=prepare_session_dir),
        encoding="utf-8",
    )

    path_dirs = [str(Path(agent_path).parent)]
    if (memu_path := shutil.which(spec.binary)) is not None:
        path_dirs.append(str(Path(memu_path).parent))
    # utf-8-sig: Windows PowerShell 5.1 runs a `-File` script in the ANSI code page
    # unless it sees a BOM, which would mangle a non-ASCII path (e.g. a CJK username)
    # baked into the wrapper. The BOM makes both 5.1 and 7 decode it as UTF-8.
    wrapper.write_text(
        wrapper_script(
            agent_path,
            spec.schedule_command,
            prompt_file,
            log_file,
            path_dirs,
            prompt_stdin=spec.schedule_prompt_stdin,
        ),
        encoding="utf-8-sig",
    )

    proc = _run_powershell(register_script(spec.task_name, wrapper, interval_minutes, layout.base))
    if proc.returncode != 0:
        print(f"error: Task Scheduler registration failed: {proc.stderr.strip()}", file=sys.stderr)
        return 1

    registry.write_text(
        json.dumps(
            {"task_name": spec.task_name, "task_path": TASK_PATH, "wrapper": str(wrapper), "prompt": str(prompt_file)},
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"registered/updated '{TASK_PATH}{spec.task_name}' — runs every {interval_minutes} min, "
        "hidden, catches up if missed"
    )
    print(f"  wrapper: {wrapper}")
    print(f"  verify it can actually run:  {spec.binary} schedule verify")
    return 0


def uninstall(spec: HostSpec, layout: Layout) -> int:
    """Remove the task by its canonical name and clean up generated artifacts."""
    _require_windows()
    proc = _run_powershell(unregister_script(spec.task_name))
    if proc.returncode == 0:
        print(f"removed '{TASK_PATH}{spec.task_name}'")
    else:
        # Idempotent: an absent task is a warning, not a failure — uninstall should
        # succeed whether or not install ever did.
        print(f"warning: could not remove '{TASK_PATH}{spec.task_name}': {proc.stderr.strip()}", file=sys.stderr)

    wrapper, prompt_file, _log, registry = _paths(layout)
    for artifact in (wrapper, prompt_file, registry):
        artifact.unlink(missing_ok=True)
    print(f"  (kept the run log {layout.base / LOG_NAME} if present)")
    return 0


def status(spec: HostSpec, layout: Layout) -> int:
    """Print whether the task is registered and its last/next run."""
    _require_windows()
    proc = _run_powershell(status_script(spec.task_name))
    if proc.returncode == 0:
        print(proc.stdout.strip())
    else:
        print(f"not registered: '{TASK_PATH}{spec.task_name}' (run `{spec.binary} schedule install`)")
    return 0


def verify(spec: HostSpec, layout: Layout) -> int:
    """Prove one task is registered and its agent CLI can run headless.

    Deliberately does not trigger a full pipeline run (that would memorize real
    sessions as a side effect); it checks the things that silently break the
    record seam, then points at the filesystem traces to watch after the next real
    run — the same "trust traces, not the run's self-report" rule the cron guide uses.
    """
    _require_windows()
    registered = _run_powershell(status_script(spec.task_name)).returncode == 0
    if not registered:
        print(f"not registered: '{TASK_PATH}{spec.task_name}' (run `{spec.binary} schedule install`)", file=sys.stderr)
        return 1

    agent_path = _resolve_agent(spec)
    if agent_path is None:
        print(
            f"error: `{_agent_binary(spec)}` is no longer a file-backed PowerShell command (memU#538 Symptom A)",
            file=sys.stderr,
        )
        return 1
    layout.base.mkdir(parents=True, exist_ok=True)
    if (rc := _launch_gate(spec, agent_path, layout.base)) != 0:
        return rc
    if (rc := _auth_gate(spec, agent_path, layout.base)) != 0:
        return rc

    print(
        f"preflight ok: '{TASK_PATH}{spec.task_name}' is registered and the exact PowerShell "
        f"command for `{_agent_binary(spec)}` launches"
    )
    if spec.needs_headless_auth:
        print("  its headless-auth probe also passed; credentials must remain persistent for the S4U run")
    print(
        "  this does not prove the S4U identity can run it; trigger the registered task, then confirm by traces:\n"
        f"    - {layout.jobs} timestamps advanced, and\n"
        f"    - {layout.session_manifest} moved"
    )
    return 0
