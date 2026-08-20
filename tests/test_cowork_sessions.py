"""Cowork audit reader: outer sessions, bounded discovery, and Claude bridge composition."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from memu.hosts.base import RecordKind
from memu.hosts.bridging.transcripts import prepare_transcripts
from memu.hosts.claude_code.desktop_sessions import ClaudeDesktopTranscriptSource
from memu.hosts.cowork.sessions import (
    CoworkTranscriptSource,
    linux_data_roots,
    macos_data_roots,
    platform_data_roots,
    windows_data_roots,
)

FIXTURE = Path(__file__).parent / "fixtures" / "cowork" / "audit.jsonl"


def _audit(root: Path, session: str) -> Path:
    path = root / "local-agent-mode-sessions" / "account" / "organization" / f"local_{session}" / "audit.jsonl"
    path.parent.mkdir(parents=True)
    shutil.copyfile(FIXTURE, path)
    return path


def test_cowork_discovers_outer_workspace_and_normalizes_records(tmp_path: Path) -> None:
    audit = _audit(tmp_path, "outer-session")
    key = audit.parent / ".audit-key"
    key.write_text("never read", encoding="utf-8")
    source = CoworkTranscriptSource([tmp_path])

    assert source.discover() == [audit]
    assert source.session_id(audit) == "outer-session"
    assert source.key(audit).startswith("cowork/")

    records = source.read_records(audit)
    assert len(records) == 4
    assert [source.classify(record) for record in records] == [
        RecordKind.MESSAGE,
        RecordKind.TOOL,
        RecordKind.TOOL,
        RecordKind.MESSAGE,
    ]
    parsed = [json.loads(record) for record in records]
    assert all(entry["source"] == {"surface": "cowork", "container": "cowork_audit_jsonl"} for entry in parsed)
    assert all("session_id" not in entry and "_audit_hmac" not in entry for entry in parsed)
    assert parsed[0]["timestamp"] == "2026-08-14T09:00:00Z"
    assert key.read_text(encoding="utf-8") == "never read"


def test_cowork_uses_audit_timestamp_when_message_timestamp_is_missing(tmp_path: Path) -> None:
    audit = _audit(tmp_path, "outer-session")
    audit.write_text(
        json.dumps({
            "type": "user",
            "_audit_timestamp": "2026-08-20T07:00:00.000Z",
            "message": {"role": "user", "content": "hello"},
        })
        + "\n",
        encoding="utf-8",
    )

    [record] = CoworkTranscriptSource([tmp_path]).read_records(audit)

    assert json.loads(record)["timestamp"] == "2026-08-20T07:00:00.000Z"


def test_windows_roots_enumerate_desktop_and_msix_locations(monkeypatch, tmp_path: Path) -> None:
    appdata = tmp_path / "Roaming"
    local = tmp_path / "Local"
    roots = (
        appdata / "Claude",
        local / "Claude-3p",
        local / "Packages" / "Claude_123" / "LocalCache" / "Roaming" / "Claude",
        local / "Packages" / "Claude_456" / "LocalCache" / "Roaming" / "Claude",
    )
    for root in roots:
        root.mkdir(parents=True)
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(local))

    assert windows_data_roots() == sorted((root.resolve() for root in roots), key=lambda root: str(root).lower())


def test_platform_roots_select_only_the_current_platform(monkeypatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    support = home / "Library" / "Application Support"
    xdg = tmp_path / "xdg"
    macos = (support / "Claude", support / "Claude-3p")
    linux = (xdg / "Claude", xdg / "Claude-3p")
    windows = tmp_path / "Roaming" / "Claude"
    for root in (*macos, *linux, windows):
        root.mkdir(parents=True)
    monkeypatch.setattr("memu.hosts.cowork.sessions.Path.home", lambda: home)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))

    monkeypatch.setattr("memu.hosts.cowork.sessions.sys.platform", "darwin")
    assert platform_data_roots() == [root.resolve() for root in macos]
    assert macos_data_roots() == [root.resolve() for root in macos]

    monkeypatch.setattr("memu.hosts.cowork.sessions.sys.platform", "linux")
    assert platform_data_roots() == [root.resolve() for root in linux]
    assert linux_data_roots() == [root.resolve() for root in linux]

    monkeypatch.setattr("memu.hosts.cowork.sessions.sys.platform", "win32")
    assert platform_data_roots() == [windows.resolve()]


def test_linux_root_defaults_to_home_config(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / ".config" / "Claude"
    root.mkdir(parents=True)
    monkeypatch.setattr("memu.hosts.cowork.sessions.Path.home", lambda: tmp_path)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    assert linux_data_roots() == [root.resolve()]


def test_cowork_roots_override_replaces_platform_discovery(monkeypatch, tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    automatic = tmp_path / "automatic" / "Claude"
    for root in (first, second, automatic):
        root.mkdir(parents=True)
    monkeypatch.setattr("memu.hosts.cowork.sessions.sys.platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "automatic"))
    monkeypatch.setenv("MEMU_COWORK_ROOTS", os.pathsep.join((str(second), "", str(first), str(first))))

    expected = tuple(sorted((first.resolve(), second.resolve()), key=lambda root: str(root).lower()))
    assert tuple(platform_data_roots()) == expected
    assert CoworkTranscriptSource().roots == expected


def test_cowork_roots_override_rejects_missing_directories(monkeypatch, tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    monkeypatch.setenv("MEMU_COWORK_ROOTS", str(missing))

    with pytest.raises(ValueError, match="MEMU_COWORK_ROOTS entries are not directories"):
        platform_data_roots()


def test_empty_cowork_roots_override_disables_discovery(monkeypatch, tmp_path: Path) -> None:
    automatic = tmp_path / "Claude"
    automatic.mkdir()
    monkeypatch.setattr("memu.hosts.cowork.sessions.sys.platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("MEMU_COWORK_ROOTS", "")

    source = CoworkTranscriptSource()
    assert platform_data_roots() == []
    assert not source.exists()
    assert source.root() == automatic


def test_constructor_roots_take_priority_over_environment(monkeypatch, tmp_path: Path) -> None:
    explicit = tmp_path / "explicit"
    overridden = tmp_path / "overridden"
    explicit.mkdir()
    overridden.mkdir()
    monkeypatch.setenv("MEMU_COWORK_ROOTS", str(overridden))

    assert CoworkTranscriptSource([explicit]).roots == (explicit.resolve(),)


def test_unknown_platform_has_no_automatic_cowork_roots(monkeypatch) -> None:
    monkeypatch.setattr("memu.hosts.cowork.sessions.sys.platform", "freebsd")
    monkeypatch.delenv("MEMU_COWORK_ROOTS", raising=False)

    assert platform_data_roots() == []


def test_combined_source_keeps_regions_independent(tmp_path: Path) -> None:
    code = tmp_path / "code"
    code.mkdir()
    old_code = code / "old.jsonl"
    old_code.write_text('{"type":"user","message":{"role":"user","content":"old"}}\n', encoding="utf-8")
    cowork = _audit(tmp_path / "cowork", "outer-session")
    os.utime(old_code, (100, 100))
    os.utime(cowork, (200, 200))
    source = ClaudeDesktopTranscriptSource(code, [tmp_path / "cowork"])

    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({source.key(cowork): {"lines": 4}}), encoding="utf-8")
    written = prepare_transcripts(
        source,
        out_dir=tmp_path / "out",
        manifest_path=manifest,
        max_jobs=10,
        pending_path=tmp_path / "pending.json",
    )

    assert written == 1
    staged = json.loads((tmp_path / "pending.json").read_text(encoding="utf-8"))
    assert source.key(old_code) in staged
    assert source.key(cowork) in staged


def test_combined_source_keeps_cowork_roots_independent(tmp_path: Path) -> None:
    code = tmp_path / "code"
    code.mkdir()
    first = _audit(tmp_path / "cowork-a", "settled")
    second = _audit(tmp_path / "cowork-b", "pending")
    os.utime(first, (200, 200))
    os.utime(second, (100, 100))
    source = ClaudeDesktopTranscriptSource(code, [tmp_path / "cowork-a", tmp_path / "cowork-b"])

    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({source.key(first): {"lines": 4}}), encoding="utf-8")
    written = prepare_transcripts(
        source,
        out_dir=tmp_path / "out",
        manifest_path=manifest,
        max_jobs=10,
        pending_path=tmp_path / "pending.json",
    )

    assert written == 1
    staged = json.loads((tmp_path / "pending.json").read_text(encoding="utf-8"))
    assert source.key(first) in staged
    assert source.key(second) in staged


def test_combined_source_preserves_code_self_skip_identity(tmp_path: Path) -> None:
    code = tmp_path / "code"
    code.mkdir()
    own = code / "scheduled-session.jsonl"
    own.write_text('{"type":"user","message":{"role":"user","content":"skip"}}\n', encoding="utf-8")
    cowork = _audit(tmp_path / "cowork", "outer-session")
    source = ClaudeDesktopTranscriptSource(code, [tmp_path / "cowork"])

    assert source.session_id(own) == "scheduled-session"
    assert source.key(own) == "scheduled-session.jsonl"
    assert source.session_id(cowork) == "outer-session"
