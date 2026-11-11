"""Hermes legacy schedule cleanup must prove removal before enabling hooks."""

from __future__ import annotations

import dataclasses
import shutil
import subprocess

import pytest

from memu.hosts.bridging import Layout
from memu.hosts.hermes import hook_install, install
from memu.hosts.hermes.cli import SPEC, main
from memu.hosts.host_cli import run
from memu.hosts.scheduling import windows


@pytest.mark.parametrize("action", ["status", "uninstall"])
@pytest.mark.parametrize("code", [0, 1])
def test_cli_propagates_cleanup_result(monkeypatch, tmp_path, action, code):
    monkeypatch.setattr(windows.platform, "system", lambda: "Windows")
    scripts = []

    def execute(script):
        scripts.append(script)
        return subprocess.CompletedProcess([], code, '{"matched":0,"removed":0}', "inspection/removal failed")

    monkeypatch.setattr(windows, "_run_powershell", execute)
    artifact = tmp_path / windows.WRAPPER_NAME
    artifact.write_text("preserve for retry", encoding="utf-8")
    assert main(["schedule", action, "--base-dir", str(tmp_path)]) == code
    assert len(scripts) == 1
    assert artifact.read_text(encoding="utf-8") == "preserve for retry"
    assert ("Unregister-ScheduledTask" in scripts[0]) is (action == "uninstall")


def test_script_checks_all_ownership_before_removal_and_reads_back(tmp_path):
    spec = dataclasses.replace(SPEC, former_task_names=("memu-old-hermes",))
    script = windows.cleanup_script(spec, Layout.default("hermes", tmp_path), remove=True)
    assert "SilentlyContinue" not in script
    assert script.index("Unrecognized legacy task action") < script.index("Unregister-ScheduledTask")
    assert script.index("Unregister-ScheduledTask") < script.index("$remaining")
    assert "-ErrorAction Stop" in script and "exit 1" in script
    assert all(name in script for name in spec.all_task_names)
    assert "TaskPath -eq '\\memU\\'" in script
    assert str(tmp_path / windows.WRAPPER_NAME) in script
    assert ".WorkingDirectory -ne" in script


@pytest.mark.parametrize("system", ["Linux", "Darwin"])
@pytest.mark.parametrize("action", ["status", "uninstall"])
def test_unverified_platform_does_not_report_success(monkeypatch, tmp_path, system, action):
    monkeypatch.setattr(windows.platform, "system", lambda: system)
    monkeypatch.setattr(windows, "_run_powershell", lambda _: pytest.fail("must not execute PowerShell"))
    assert run(SPEC, ["schedule", action, "--base-dir", str(tmp_path)]) == 1


@pytest.mark.skipif(shutil.which("powershell.exe") is None, reason="requires Windows PowerShell")
@pytest.mark.parametrize("failure", ["inspection", "ownership", "removal", "readback", "still-present"])
def test_powershell_failures_return_nonzero(tmp_path, failure):
    layout = Layout.default("hermes", tmp_path)
    quote = windows._ps_quote
    arguments = f'-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{tmp_path / windows.WRAPPER_NAME}"'
    # Shadow scheduler cmdlets: execute the real generated script without touching real tasks.
    setup = "\n".join([
        f"$script:failure = {quote(failure)}; $script:reads = 0",
        f"$script:task = [pscustomobject]@{{TaskName={quote(SPEC.task_name)}; TaskPath={quote(windows.TASK_PATH)}; "
        f"Actions=@([pscustomobject]@{{Execute='powershell.exe'; Arguments={quote(arguments)}; "
        f"WorkingDirectory={quote(str(tmp_path))}}})}}",
        "function Get-ScheduledTask { [CmdletBinding()] param()",
        "$script:reads++",
        "if ($script:failure -eq 'inspection') { throw 'inspection denied' }",
        "if ($script:failure -eq 'ownership') { $script:task.Actions[0].Arguments = 'user command' }",
        "if ($script:reads -gt 1 -and $script:failure -eq 'readback') { throw 'readback denied' }",
        "if ($script:reads -eq 1 -or $script:failure -eq 'still-present') { $script:task }",
        "}",
        "function Unregister-ScheduledTask { [CmdletBinding(SupportsShouldProcess=$true)] param($InputObject)",
        "if ($script:failure -eq 'removal') { throw 'removal denied' }",
        "}",
    ])
    result = windows._run_powershell(setup + "\n" + windows.cleanup_script(SPEC, layout, remove=True))
    assert result.returncode != 0, result.stdout
    assert result.stderr.strip()


@pytest.mark.parametrize("operation", ["install", "uninstall"])
def test_cleanup_failure_stops_plugin_changes(monkeypatch, tmp_path, operation):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes"))
    monkeypatch.setattr(install.platform, "system", lambda: "Windows")
    commands = []

    async def command(argv):
        commands.append(argv)
        return 1

    monkeypatch.setattr(install, "_command", command)
    monkeypatch.setattr(hook_install, "install", lambda _: pytest.fail("must not install hooks"))
    monkeypatch.setattr(hook_install, "command", lambda *a: pytest.fail("must not remove plugin"))
    import argparse
    import asyncio

    args = argparse.Namespace(base_dir=tmp_path, json=True)
    if operation == "install":
        with pytest.raises(install.lifecycle.Blocked, match="cleanup failed"):
            asyncio.run(install._stage(3, args))
    else:
        assert asyncio.run(hook_install.remove(args)) == 1
    assert commands == [["schedule", "uninstall", "--base-dir", str(tmp_path)]]
