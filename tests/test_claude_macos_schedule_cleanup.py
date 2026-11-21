"""Legacy macOS cleanup must prove action ownership and preserve retry state."""

from __future__ import annotations

import json
import plistlib
import subprocess
from pathlib import Path

import pytest

from memu.hosts.claude_code.cli import main
from memu.hosts.scheduling import macos

PROMPT = "Run the memU bridging pipeline. ~/.memu/hosts/claude-code/jobs/ memu-claude-code prepare then memu-claude-code commit"
ACTION = ["/usr/local/bin/claude", "-p", PROMPT]
CRON = f"0 * * * * /usr/local/bin/claude -p '{PROMPT}'\n".encode()


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    directory = tmp_path / "LaunchAgents"
    directory.mkdir()
    monkeypatch.setattr(macos, "_locations", lambda: [(directory, ("gui/501",))])
    monkeypatch.setattr(macos, "_cron_users", lambda: (None,))
    monkeypatch.setattr(macos, "_read_cron", lambda user: b"")
    monkeypatch.setattr(macos, "_system_crontab", lambda: tmp_path / "absent-crontab")
    return directory


def plist(directory, *, label="unusual-label", args=None, **extra):
    path = directory / f"{label}.plist"
    path.write_bytes(plistlib.dumps({"Label": label, "ProgramArguments": args or ACTION, **extra}))
    return path


@pytest.mark.parametrize("action", ["status", "uninstall"])
def test_cli_propagates_mac_cleanup(monkeypatch, tmp_path, action):
    monkeypatch.setattr("memu.hosts.claude_code.cli.platform.system", lambda: "Darwin")
    called = []

    def cleanup(**kwargs):
        called.append(kwargs)
        return 1

    monkeypatch.setattr(macos, "cleanup", cleanup)
    assert main(["schedule", action, "--base-dir", str(tmp_path)]) == 1
    assert called == [{"remove": action == "uninstall"}]


@pytest.mark.parametrize("argv", [ACTION, ["claude", "--print", PROMPT], ["/bin/sh", "-c", f"claude -p '{PROMPT}'"]])
def test_recognizes_actual_inline_bridge(argv):
    assert macos._is_bridge(argv)


@pytest.mark.parametrize(
    "argv",
    [
        ["echo", *ACTION],
        ["claude", "-p", "just memu-claude-code prepare"],
        ["claude", "-p", PROMPT.replace("claude-code", "codex")],
        ["claude", "-p", "not-memu-claude-code prepare and memu-claude-code commit"],
        ["/bin/sh", "-c", "'unterminated"],
        ["/user/scheduler/memu-bridging-claude-code"],
    ],
)
def test_unproven_actions_are_not_owned(argv):
    assert not macos._is_bridge(argv)


def test_inspect_reads_action_not_name_and_preserves_uncertain(isolated):
    owned = plist(isolated)
    unknown = plist(isolated, label="memu-remember-claude-code", args=["/bin/echo", "hello"])
    other = plist(isolated, label="other-host", args=["claude", "-p", PROMPT.replace("claude-code", "codex")])
    registrations, errors = macos.inspect()
    assert [r.path for r in registrations] == [owned]
    assert errors and "preserved" in errors[0]
    assert unknown.exists() and other.exists()


def test_program_overrides_argv_zero(isolated):
    plist(isolated, Program="/bin/echo")
    registrations, errors = macos.inspect()
    assert not registrations and errors


def test_status_never_changes_registration(isolated, monkeypatch, capsys):
    path = plist(isolated)
    before = path.read_bytes()
    monkeypatch.setattr(macos, "_job", lambda target: None)
    monkeypatch.setattr(macos, "_checked", lambda *a, **k: pytest.fail("status must not change launchd"))
    assert macos.cleanup() == 0
    assert json.loads(capsys.readouterr().out)["status"] == "registered"
    assert path.read_bytes() == before


def test_cron_preserves_env_comments_other_hosts_and_unknown():
    preserved = b"PATH=/usr/bin:/bin\n# user's comment\n@hourly echo unrelated\n"
    unrelated = CRON.replace(b"claude-code", b"codex")
    unknown = b"0 * * * * /bin/sh /user/scheduler/memu-remember-claude-code\n"
    kept, count, uncertain = macos._select_cron(preserved + CRON + unrelated + unknown)
    assert kept == preserved + unrelated + unknown and count == 1
    assert uncertain and "preserved" in uncertain[0]
    assert macos._select_cron(b"@reboot root " + CRON.split(b" ", 5)[5], system=True)[1] == 1


def test_crontab_missing_vs_permission(monkeypatch):
    monkeypatch.setattr(macos, "_run", lambda *a, **k: subprocess.CompletedProcess([], 1, b"", b"no crontab for user"))
    assert macos._read_cron(None) == b""
    monkeypatch.setattr(macos, "_run", lambda *a, **k: subprocess.CompletedProcess([], 1, b"", b"permission denied"))
    with pytest.raises(RuntimeError, match="permission denied"):
        macos._read_cron("root")


@pytest.mark.parametrize("failure", ["inspection", "disable", "bootout", "readback", "running"])
def test_launchd_failures_preserve_retry_plist(isolated, monkeypatch, failure):
    path = plist(isolated)
    original = path.read_bytes()
    calls = []
    jobs = iter([b"state = waiting", b"pid = 123\n" if failure == "running" else b"state = waiting", b"still exists"])

    def job(target):
        if failure == "inspection":
            msg = "inspection denied"
            raise RuntimeError(msg)
        return next(jobs)

    def checked(argv, **kwargs):
        calls.append(argv[1])
        if argv[1] == failure:
            msg = f"{failure} denied"
            raise RuntimeError(msg)
        return b""

    monkeypatch.setattr(macos, "_job", job)
    monkeypatch.setattr(macos, "_checked", checked)
    assert macos.cleanup(remove=True) == 1
    assert path.read_bytes() == original
    if failure == "running":
        assert calls == ["disable"]  # Never bootout/kill a known running agent.


def test_launchd_unload_then_absence_before_unlink(isolated, monkeypatch):
    path = plist(isolated)
    states = iter([b"waiting", b"waiting", None])
    calls = []
    monkeypatch.setattr(macos, "_job", lambda target: next(states))

    def checked(argv):
        calls.append(argv)
        return b""

    monkeypatch.setattr(macos, "_checked", checked)
    assert macos.cleanup(remove=True) == 0
    assert [c[1] for c in calls] == ["disable", "bootout"]
    assert all(c[-1] == "gui/501/unusual-label" for c in calls)
    assert not path.exists()
    assert macos.cleanup(remove=True) == 0


def test_cron_change_and_readback_failure(isolated, monkeypatch):
    item = macos.Registration("user", "crontab", CRON, retained=b"")
    monkeypatch.setattr(macos, "inspect", lambda: ([item], []))
    monkeypatch.setattr(macos, "_read_cron", lambda user: b"concurrent edit")
    monkeypatch.setattr(macos, "_checked", lambda *a, **k: pytest.fail("must preserve concurrent edit"))
    assert macos.cleanup(remove=True) == 1
    states = iter([CRON, CRON])
    monkeypatch.setattr(macos, "_read_cron", lambda user: next(states))
    monkeypatch.setattr(macos, "_checked", lambda *a, **k: b"")
    assert macos.cleanup(remove=True) == 1


def test_cron_targeted_removal_preserves_bytes(isolated, monkeypatch):
    remaining = b"PATH=/usr/bin\n0 * * * * echo user job\n"
    stored = [CRON + remaining]
    monkeypatch.setattr(macos, "_read_cron", lambda user: stored[0])

    def checked(argv, *, data):
        assert argv == ["/usr/bin/crontab", "-"]
        stored[0] = data
        return b""

    monkeypatch.setattr(macos, "_checked", checked)
    assert macos.cleanup(remove=True) == 0
    assert stored == [remaining]


def test_system_cron_atomic_replacement_and_mode(isolated, monkeypatch, tmp_path):
    path = tmp_path / "system-cron"
    original = b"# system header\n" + b"0 * * * * root " + CRON.split(b" ", 5)[5] + b"@hourly daemon echo other\n"
    path.write_bytes(original)
    path.chmod(0o640)
    monkeypatch.setattr(macos, "_system_crontab", lambda: path)
    assert macos.cleanup(remove=True) == 0
    assert path.read_bytes() == b"# system header\n@hourly daemon echo other\n"
    assert path.stat().st_mode & 0o777 == 0o640


def test_symlink_and_inspection_failure_are_not_absent(isolated, monkeypatch, tmp_path):
    target = tmp_path / "outside.plist"
    target.write_bytes(plistlib.dumps({"Label": "keep", "ProgramArguments": ACTION}))
    (isolated / "link.plist").symlink_to(target)
    assert macos.cleanup(remove=True) == 1 and target.exists()
    monkeypatch.setattr(macos, "_read_cron", lambda user: (_ for _ in ()).throw(PermissionError("denied")))
    assert macos.cleanup() == 1


@pytest.mark.parametrize("label", ["memu-remember-claude-code", "memu-bridging-claude-code", "unexpected-name"])
def test_all_historical_and_nonstandard_names_use_actions(isolated, label):
    path = plist(isolated, label=label)
    assert [r.path for r in macos.inspect()[0]] == [path]


def test_shared_agent_never_unloads_only_one_users_job(monkeypatch):
    item = macos.Registration("shared", "launchd", b"", path=Path("/Library/LaunchAgents/test.plist"))
    monkeypatch.setattr(macos, "_job", lambda *args: pytest.fail("must verify all users before shared unload"))
    with pytest.raises(RuntimeError, match="all-user domain"):
        macos._remove_launchd(item)


def test_malformed_and_unreadable_plists_are_visible(isolated, monkeypatch):
    path = isolated / "malformed.plist"
    path.write_bytes(b"not a plist")
    assert macos.cleanup() == 1
    path.unlink()
    monkeypatch.setattr(macos, "_read_file", lambda *args: (_ for _ in ()).throw(PermissionError("denied")))
    plist(isolated)
    assert macos.cleanup() == 1


def test_unload_readback_permission_is_not_absence(isolated, monkeypatch):
    plist(isolated)
    states = iter([b"waiting", b"waiting"])

    def job(target):
        try:
            return next(states)
        except StopIteration:
            msg = "readback denied"
            raise PermissionError(msg) from None

    monkeypatch.setattr(macos, "_job", job)
    monkeypatch.setattr(macos, "_checked", lambda *a: b"")
    assert macos.cleanup(remove=True) == 1
    assert len(list(isolated.iterdir())) == 1
