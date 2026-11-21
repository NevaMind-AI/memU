"""Opt-in real launchd lifecycle; only newly created private test services are touched."""

from __future__ import annotations

import json
import os
import plistlib
import sys
import time
import uuid

import pytest

from memu.hosts.scheduling import macos

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin" or os.environ.get("MEMU_TEST_LAUNCHD") != "1",
    reason="explicit opt-in to real macOS launchd fixture required",
)


@pytest.mark.parametrize("running", [False, True])
def test_own_launchd_fixture_lifecycle(tmp_path, monkeypatch, capsys, running):
    domain = f"gui/{os.getuid()}"
    label = f"ai.memu.contribution-test.{uuid.uuid4().hex}"
    target = f"{domain}/{label}"
    directory = tmp_path / "agents"
    directory.mkdir()
    # A harmless fixture binary named claude, not a user's agent executable.
    executable = tmp_path / "claude"
    executable.write_text("#!/bin/sh\nexec /bin/sleep 3\n")
    executable.chmod(0o700)
    prompt = "Run the memU bridging pipeline. ~/.memu/hosts/claude-code/jobs/ memu-claude-code prepare then memu-claude-code commit"
    path = directory / f"{label}.plist"
    path.write_bytes(
        plistlib.dumps({"Label": label, "ProgramArguments": [str(executable), "-p", prompt], "RunAtLoad": running})
    )
    other = directory / "unrelated.plist"
    other.write_bytes(plistlib.dumps({"Label": "unrelated-fixture", "ProgramArguments": ["/usr/bin/true"]}))
    before = other.read_bytes()
    # Narrow discovery to our new fixture; do not inspect/remove existing user jobs.
    monkeypatch.setattr(macos, "_locations", lambda: [(directory, (domain,))])
    monkeypatch.setattr(macos, "_cron_users", lambda: ())
    monkeypatch.setattr(macos, "_system_crontab", lambda: tmp_path / "absent-cron")
    macos._checked(["/bin/launchctl", "bootstrap", domain, str(path)])
    try:
        if running:
            deadline = time.monotonic() + 5
            while b"pid = " not in (macos._job(target) or b""):
                assert time.monotonic() < deadline
                time.sleep(0.05)
        assert macos.cleanup() == 0
        status = json.loads(capsys.readouterr().out)
        assert status["registrations"][0]["loaded_domains"] == [domain]
        if running:
            assert macos.cleanup(remove=True) == 1
            assert path.exists() and b"pid = " in (macos._job(target) or b"")
            deadline = time.monotonic() + 8
            while b"pid = " in (macos._job(target) or b""):
                assert time.monotonic() < deadline
                time.sleep(0.05)
        assert macos.cleanup(remove=True) == 0
        assert not path.exists() and macos._job(target) is None
        assert other.read_bytes() == before
        assert macos.cleanup(remove=True) == 0
    finally:
        # Fixture only. Let its harmless sleep finish before unloading on failure.
        deadline = time.monotonic() + 8
        while b"pid = " in (macos._job(target) or b"") and time.monotonic() < deadline:
            time.sleep(0.05)
        if macos._job(target) is not None:
            macos._checked(["/bin/launchctl", "bootout", target])
        macos._checked(["/bin/launchctl", "enable", target])
