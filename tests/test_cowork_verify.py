"""The Cowork diagnostic proves the composed source contract without ingesting data."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from memu.hosts.claude_code import cowork_cmd
from memu.hosts.claude_code.cli import SPEC, main
from memu.hosts.claude_code.desktop_sessions import ClaudeDesktopTranscriptSource
from memu.hosts.host_cli import build_parser

FIXTURE = Path(__file__).parent / "fixtures" / "cowork" / "audit.jsonl"


def _audit(root: Path, session: str) -> Path:
    path = root / "local-agent-mode-sessions" / "account" / "organization" / f"local_{session}" / "audit.jsonl"
    path.parent.mkdir(parents=True)
    shutil.copyfile(FIXTURE, path)
    return path


def _code_session(root: Path, session: str, *, timestamp: str, content: str) -> Path:
    path = root / "project" / f"{session}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "type": "user",
            "timestamp": timestamp,
            "message": {"role": "user", "content": content},
        })
        + "\n",
        encoding="utf-8",
    )
    return path


def _files(root: Path) -> dict[str, tuple[int, int]]:
    return {
        path.relative_to(root).as_posix(): (path.stat().st_mtime_ns, path.stat().st_size)
        for path in root.rglob("*")
        if path.is_file()
    }


def test_parser_exposes_one_repeatable_cowork_verify_surface(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()

    args = build_parser(SPEC).parse_args(["cowork", "verify", "--root", str(first), "--root", str(second)])

    assert args.cowork_action == "verify"
    assert args.root == [first.resolve(), second.resolve()]


def test_explicit_missing_root_is_an_argument_error(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["cowork", "verify", "--root", str(tmp_path / "missing")])

    assert excinfo.value.code == 2


def test_automatic_zero_roots_is_a_successful_warning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MEMU_COWORK_ROOTS", "")
    monkeypatch.setattr(cowork_cmd, "SESSION_DIR", str(tmp_path / "no-code"))

    assert main(["cowork", "verify"]) == 0

    output = capsys.readouterr().out
    assert "mode                       environment" in output
    assert "Cowork sessions            0" in output
    assert "[WARN] Readable" in output
    assert "[WARN] Separation" in output
    assert "[WARN] File timeline" in output
    assert output.rstrip().endswith("RESULT WARN")


def test_automatic_mode_uses_platform_discovery(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("MEMU_COWORK_ROOTS", raising=False)
    monkeypatch.setattr(cowork_cmd, "SESSION_DIR", str(tmp_path / "no-code"))
    monkeypatch.setattr("memu.hosts.cowork.sessions.platform_data_roots", lambda: [])

    assert main(["cowork", "verify"]) == 0

    output = capsys.readouterr().out
    assert "mode                       automatic" in output
    assert output.rstrip().endswith("RESULT WARN")


def test_explicit_empty_root_is_a_successful_warning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "cowork"
    root.mkdir()
    monkeypatch.setattr(cowork_cmd, "SESSION_DIR", str(tmp_path / "no-code"))

    assert main(["cowork", "verify", "--root", str(root)]) == 0

    output = capsys.readouterr().out
    assert "mode                       explicit" in output
    assert f"root {root.resolve()} (0 session(s))" in output
    assert output.rstrip().endswith("RESULT WARN")


def test_clean_mixed_sources_pass_all_dimensions_without_writes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code_root = tmp_path / "code"
    cowork_root = tmp_path / "cowork"
    code = _code_session(code_root, "code-session", timestamp="2026-08-14T08:00:00Z", content="code only")
    audit = _audit(cowork_root, "cowork-session")
    os.utime(code, ns=(100_000_000_000, 100_000_000_000))
    os.utime(audit, ns=(200_000_000_000, 200_000_000_000))
    before = _files(tmp_path)
    monkeypatch.setattr(cowork_cmd, "SESSION_DIR", str(code_root))

    assert main(["cowork", "verify", "--root", str(cowork_root)]) == 0

    output = capsys.readouterr().out
    assert "root " in output and "(1 session(s))" in output
    assert "[PASS] Readable" in output
    assert "readable sessions          1 / 1" in output
    assert "normalized records         4" in output
    assert "normalized messages        2" in output
    assert "[PASS] Separation" in output
    assert "session-ID intersection    0" in output
    assert "exact message overlap      0" in output
    assert "[PASS] File timeline" in output
    assert "composite files            2 = 1 + 1" in output
    assert "mtime order                non-increasing" in output
    assert "Code/Cowork transitions    1" in output
    assert output.rstrip().endswith("RESULT PASS")
    assert _files(tmp_path) == before


def test_sub_float_precision_mtime_ties_follow_the_composite_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code_root = tmp_path / "code"
    cowork_root = tmp_path / "cowork"
    code = _code_session(code_root, "code-session", timestamp="2026-08-14T08:00:00Z", content="code only")
    audit = _audit(cowork_root, "cowork-session")
    base = 1_775_000_000_000_000_000
    os.utime(code, ns=(base, base))
    os.utime(audit, ns=(base + 100, base + 100))
    code_mtime = code.stat()
    audit_mtime = audit.stat()
    if code_mtime.st_mtime_ns == audit_mtime.st_mtime_ns or code_mtime.st_mtime != audit_mtime.st_mtime:
        pytest.skip("filesystem does not expose a sub-float-precision mtime tie")
    monkeypatch.setattr(cowork_cmd, "SESSION_DIR", str(code_root))

    assert main(["cowork", "verify", "--root", str(cowork_root)]) == 0

    output = capsys.readouterr().out
    assert "mtime order                non-increasing" in output
    assert output.rstrip().endswith("RESULT PASS")


def test_overlap_warns_without_printing_content_or_digests(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code_root = tmp_path / "code"
    cowork_root = tmp_path / "cowork"
    _code_session(
        code_root,
        "outer-session",
        timestamp="2026-08-14T09:00:00Z",
        content="plan the project",
    )
    _audit(cowork_root, "outer-session")
    monkeypatch.setattr(cowork_cmd, "SESSION_DIR", str(code_root))

    assert main(["cowork", "verify", "--root", str(cowork_root)]) == 0

    output = capsys.readouterr().out
    assert "[WARN] Separation" in output
    assert "session-ID intersection    1" in output
    assert "exact message overlap      1" in output
    assert "plan the project" not in output
    assert "RESULT WARN" in output


def test_read_failure_is_aggregate_and_fails_without_leaking_the_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code_root = tmp_path / "code"
    cowork_root = tmp_path / "private-cowork-root"
    _code_session(code_root, "code-session", timestamp="2026-08-14T08:00:00Z", content="code only")
    _audit(cowork_root, "private-session")
    monkeypatch.setattr(cowork_cmd, "SESSION_DIR", str(code_root))

    def unreadable(self, path: Path) -> list[str]:
        raise OSError

    monkeypatch.setattr("memu.hosts.cowork.sessions.CoworkTranscriptSource.read_records", unreadable)

    assert main(["cowork", "verify", "--root", str(cowork_root)]) == 1

    output = capsys.readouterr().out
    assert "[FAIL] Readable" in output
    assert "unreadable sessions        1" in output
    assert "private-session" not in output
    assert output.rstrip().endswith("RESULT FAIL")


def test_broken_composite_contract_fails_timeline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code_root = tmp_path / "code"
    cowork_root = tmp_path / "cowork"
    code = _code_session(code_root, "code-session", timestamp="2026-08-14T08:00:00Z", content="code only")
    audit = _audit(cowork_root, "cowork-session")
    monkeypatch.setattr(cowork_cmd, "SESSION_DIR", str(code_root))

    def duplicated(self: ClaudeDesktopTranscriptSource) -> list[Path]:
        return [audit, code, code]

    monkeypatch.setattr(ClaudeDesktopTranscriptSource, "discover", duplicated)

    assert main(["cowork", "verify", "--root", str(cowork_root)]) == 1

    output = capsys.readouterr().out
    assert "[FAIL] File timeline" in output
    assert "count additive             no" in output
    assert "paths unique               no" in output
    assert output.rstrip().endswith("RESULT FAIL")
