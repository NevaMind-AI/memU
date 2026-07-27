"""The cron bridging helper (memU#591).

Same testing shape as ``test_scheduling_windows.py``: the pure builders are
proven without touching a real crontab (so the suite is identical on macOS,
Linux, and a Windows dev box), and the executors run against a monkeypatched
in-memory crontab — never the machine's own.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from memu.hosts.bridging import Layout
from memu.hosts.claude_code.cli import SPEC as CLAUDE
from memu.hosts.cursor.cli import SPEC as CURSOR
from memu.hosts.host_cli import run
from memu.hosts.scheduling import prompt, unix

# ---------------------------------------------------------------------------
# Pure builders
# ---------------------------------------------------------------------------


def test_cron_expression_hourly_and_subhourly() -> None:
    assert unix.cron_expression(60) == "0 * * * *"
    assert unix.cron_expression(15) == "*/15 * * * *"
    for bad in (0, -5, 61):
        with pytest.raises(ValueError, match="interval"):
            unix.cron_expression(bad)


def test_shell_invocation_maps_prompt_placeholder() -> None:
    assert unix.shell_invocation("/usr/local/bin/claude", "claude -p {prompt}") == (
        '/usr/local/bin/claude -p "$prompt"'
    )
    # cursor's template flows --trust through, same as the PowerShell builder.
    assert unix.shell_invocation("/x/cursor-agent", CURSOR.schedule_command) == '/x/cursor-agent --trust -p "$prompt"'


def test_bridge_script_keeps_prompt_off_the_command_line(tmp_path: Path) -> None:
    text = unix.bridge_script("/usr/local/bin/claude", "claude -p {prompt}", tmp_path, ["/usr/local/bin"])
    # The prompt is read from the file into $prompt, then passed as one argument —
    # the whole point (memU#591): nothing long ever hits a scheduler-parsed line.
    assert f'prompt=$(cat "$DIR/{unix.PROMPT_NAME}")' in text
    assert '"$prompt"' in text
    # PATH is baked into the script, not written as a file-global crontab env line.
    assert 'PATH=/usr/local/bin:"$PATH"; export PATH' in text
    # The single-instance lock and its documented reclaim tradeoff.
    assert 'mkdir "$LOCK"' in text
    assert "-mmin +180" in text
    assert "double-run" in text
    # Workspace trust must land on memU's own tree (cursor's --trust).
    assert 'cd "$DIR" || exit 1' in text


def test_bridge_script_quotes_apostrophe_paths(tmp_path: Path) -> None:
    base = tmp_path / "O'Brien"
    text = unix.bridge_script("/x/claude", "claude -p {prompt}", base, ["/x"])
    assert "DIR='" in text  # shlex-quoted, so the apostrophe cannot end the string
    assert "O'\"'\"'Brien" in text or "O'\\''Brien" in text


def test_cron_entry_is_short(tmp_path: Path) -> None:
    entry = unix.cron_entry(tmp_path / unix.SCRIPT_NAME, 60)
    assert entry.startswith("0 * * * * ")
    assert len(entry) < 512  # the regression class this whole helper exists for


def test_is_host_entry_matches_both_layouts_and_nothing_else(tmp_path: Path) -> None:
    layout = Layout.default(host="claude-code", base=tmp_path)
    ours = unix.cron_entry(tmp_path / unix.SCRIPT_NAME, 60)
    legacy = "0 * * * * claude -p 'Run the memU bridging pipeline. … ~/.memu/hosts/claude-code/jobs/ …'"
    other_host = "0 * * * * $HOME/.memu/hosts/cursor/bridge.sh"
    other_legacy = "0 * * * * cursor-agent -p 'Run the memU bridging pipeline. … ~/.memu/hosts/cursor/jobs/ …'"
    users_own = "30 4 * * * /usr/local/bin/backup.sh"
    assert unix.is_host_entry(ours, layout)
    assert unix.is_host_entry(legacy, layout)
    assert not unix.is_host_entry(other_host, layout)
    assert not unix.is_host_entry(other_legacy, layout)
    assert not unix.is_host_entry(users_own, layout)
    assert not unix.is_host_entry("# comment mentioning memU bridging pipeline hosts/claude-code/", layout)


# ---------------------------------------------------------------------------
# Executors against a fake crontab (never the machine's own)
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_crontab(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    state = {"text": ""}
    monkeypatch.setattr(unix, "_read_crontab", lambda: state["text"])

    def write(text: str) -> tuple[bool, str]:
        state["text"] = text
        return True, ""

    monkeypatch.setattr(unix, "_write_crontab", write)
    return state


@pytest.fixture
def ready_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(unix, "_resolve_agent", lambda spec: "/usr/local/bin/claude")
    monkeypatch.setattr(unix, "_auth_gate", lambda spec, path, workdir: 0)


def test_install_writes_files_and_registers_one_entry(
    fake_crontab: dict[str, str], ready_agent: None, tmp_path: Path
) -> None:
    layout = Layout.default(host="claude-code", base=tmp_path)
    fake_crontab["text"] = "30 4 * * * /usr/local/bin/backup.sh\n"
    assert unix.install(CLAUDE, layout) == 0
    script, prompt_file = tmp_path / unix.SCRIPT_NAME, tmp_path / unix.PROMPT_NAME
    assert script.stat().st_mode & 0o111  # executable
    assert prompt_file.read_text(encoding="utf-8") == prompt.bridging_pipeline_prompt(CLAUDE)
    lines = fake_crontab["text"].splitlines()
    assert "30 4 * * * /usr/local/bin/backup.sh" in lines  # the user's entry survives
    assert sum(unix.is_host_entry(line, layout) for line in lines) == 1


def test_install_migrates_a_legacy_inline_entry(
    fake_crontab: dict[str, str], ready_agent: None, tmp_path: Path
) -> None:
    layout = Layout.default(host="claude-code", base=tmp_path)
    fake_crontab["text"] = "0 * * * * claude -p 'Run the memU bridging pipeline. … ~/.memu/hosts/claude-code/jobs/ …'\n"
    assert unix.install(CLAUDE, layout) == 0
    lines = fake_crontab["text"].splitlines()
    assert not any("memU bridging pipeline" in line for line in lines)  # legacy gone
    assert sum(unix.is_host_entry(line, layout) for line in lines) == 1  # replaced, not duplicated


def test_install_is_idempotent(fake_crontab: dict[str, str], ready_agent: None, tmp_path: Path) -> None:
    layout = Layout.default(host="claude-code", base=tmp_path)
    assert unix.install(CLAUDE, layout) == 0
    assert unix.install(CLAUDE, layout) == 0
    lines = fake_crontab["text"].splitlines()
    assert sum(unix.is_host_entry(line, layout) for line in lines) == 1


def test_uninstall_removes_entry_and_artifacts_keeps_log(
    fake_crontab: dict[str, str], ready_agent: None, tmp_path: Path
) -> None:
    layout = Layout.default(host="claude-code", base=tmp_path)
    assert unix.install(CLAUDE, layout) == 0
    log = tmp_path / unix.LOG_NAME
    log.write_text("a run happened\n", encoding="utf-8")
    assert unix.uninstall(CLAUDE, layout) == 0
    assert not any(unix.is_host_entry(line, layout) for line in fake_crontab["text"].splitlines())
    assert not (tmp_path / unix.SCRIPT_NAME).exists()
    assert not (tmp_path / unix.PROMPT_NAME).exists()
    assert log.exists()  # the run log is the user's history, not our artifact


def test_uninstall_absent_entry_is_a_warning_not_a_failure(fake_crontab: dict[str, str], tmp_path: Path) -> None:
    layout = Layout.default(host="claude-code", base=tmp_path)
    assert unix.uninstall(CLAUDE, layout) == 0


def test_install_refuses_missing_agent(
    fake_crontab: dict[str, str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(unix, "_resolve_agent", lambda spec: None)
    layout = Layout.default(host="claude-code", base=tmp_path)
    assert unix.install(CLAUDE, layout) == 1
    assert fake_crontab["text"] == ""  # nothing registered on a refused install


def test_verify_green_after_install_and_catches_drift(
    fake_crontab: dict[str, str], ready_agent: None, tmp_path: Path
) -> None:
    layout = Layout.default(host="claude-code", base=tmp_path)
    assert unix.install(CLAUDE, layout) == 0
    assert unix.verify(CLAUDE, layout) == 0
    (tmp_path / unix.PROMPT_NAME).write_text("drifted", encoding="utf-8")
    assert unix.verify(CLAUDE, layout) == 1


def test_status_reports_unregistered_then_registered(
    fake_crontab: dict[str, str],
    ready_agent: None,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    layout = Layout.default(host="claude-code", base=tmp_path)
    assert unix.status(CLAUDE, layout) == 0
    assert "not registered" in capsys.readouterr().out
    assert unix.install(CLAUDE, layout) == 0
    assert unix.status(CLAUDE, layout) == 0
    out = capsys.readouterr().out
    assert "crontab:" in out
    assert "lock:" in out


def test_executors_refuse_windows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(unix.platform, "system", lambda: "Windows")
    layout = Layout.default(host="claude-code", base=tmp_path)
    for call in (
        lambda: unix.install(CLAUDE, layout),
        lambda: unix.uninstall(CLAUDE, layout),
        lambda: unix.status(CLAUDE, layout),
        lambda: unix.verify(CLAUDE, layout),
    ):
        with pytest.raises(RuntimeError):
            call()


def test_cli_schedule_dispatches_to_cron_off_windows(
    fake_crontab: dict[str, str], capsys: pytest.CaptureFixture[str]
) -> None:
    # The pre-#591 behavior — "schedule is Windows-only, go read the docs" — is
    # gone: on macOS/Linux the verb now works against cron.
    assert run(CLAUDE, ["schedule", "status"]) == 0
    assert "not registered" in capsys.readouterr().out
