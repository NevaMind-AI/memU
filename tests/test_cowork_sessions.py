"""Cowork audit reader: outer sessions, bounded discovery, and Claude bridge composition."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from memu.hosts.base import RecordKind
from memu.hosts.bridging.transcripts import prepare_transcripts
from memu.hosts.claude_code.desktop_sessions import ClaudeDesktopTranscriptSource
from memu.hosts.cowork.sessions import CoworkTranscriptSource, windows_data_roots

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
    assert key.read_text(encoding="utf-8") == "never read"


def test_windows_roots_enumerate_desktop_and_msix_locations(monkeypatch, tmp_path: Path) -> None:
    appdata = tmp_path / "Roaming"
    local = tmp_path / "Local"
    for root in (
        appdata / "Claude",
        local / "Claude-3p",
        local / "Packages" / "Claude_123" / "LocalCache" / "Roaming" / "Claude",
    ):
        root.mkdir(parents=True)
    monkeypatch.setattr("memu.hosts.cowork.sessions.sys.platform", "win32")
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(local))

    assert windows_data_roots() == [
        (appdata / "Claude").resolve(),
        (local / "Claude-3p").resolve(),
        (local / "Packages" / "Claude_123" / "LocalCache" / "Roaming" / "Claude").resolve(),
    ]


def test_cowork_is_disabled_without_a_verified_platform(monkeypatch) -> None:
    monkeypatch.setattr("memu.hosts.cowork.sessions.sys.platform", "linux")
    assert windows_data_roots() == []


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
