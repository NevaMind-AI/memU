"""Read-only diagnostics for Claude Code's composed Cowork source."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from enum import IntEnum
from itertools import pairwise
from pathlib import Path
from typing import Any

from memu.hosts.base import RecordKind, TranscriptSource
from memu.hosts.claude_code.desktop_sessions import ClaudeDesktopTranscriptSource
from memu.hosts.claude_code.sessions import SESSION_DIR, ClaudeCodeTranscriptSource
from memu.hosts.cowork.sessions import CoworkTranscriptSource


class _Status(IntEnum):
    PASS = 0
    WARN = 1
    FAIL = 2


@dataclass(frozen=True)
class _Check:
    name: str
    status: _Status
    rows: tuple[tuple[str, object], ...]


@dataclass(frozen=True)
class _Fingerprints:
    messages: int
    skipped: int
    values: frozenset[bytes]


def _directory(value: str) -> Path:
    try:
        path = Path(value).expanduser().resolve()
    except OSError as exc:
        message = f"cannot resolve directory: {value}"
        raise argparse.ArgumentTypeError(message) from exc
    if not path.is_dir():
        message = f"not a directory: {value}"
        raise argparse.ArgumentTypeError(message)
    return path


def _fingerprints(source: TranscriptSource, records_by_path: dict[Path, list[str]]) -> _Fingerprints:
    messages = 0
    skipped = 0
    values: set[bytes] = set()
    for records in records_by_path.values():
        for record in records:
            if source.classify(record) is not RecordKind.MESSAGE:
                continue
            messages += 1
            try:
                entry = json.loads(record)
                message = entry["message"]
                timestamp = entry["timestamp"]
                role = message["role"]
                content = message["content"]
            except (KeyError, TypeError, json.JSONDecodeError):
                skipped += 1
                continue
            if not isinstance(timestamp, str) or not isinstance(role, str):
                skipped += 1
                continue
            try:
                canonical = json.dumps(
                    [timestamp, role, content],
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            except (TypeError, ValueError):
                skipped += 1
                continue
            values.add(hashlib.sha256(canonical.encode()).digest())
    return _Fingerprints(messages, skipped, frozenset(values))


def _read_all(source: TranscriptSource, paths: list[Path]) -> tuple[dict[Path, list[str]], int]:
    records: dict[Path, list[str]] = {}
    errors = 0
    for path in paths:
        try:
            records[path] = source.read_records(path)
        except Exception:  # Each failure is reported only as an aggregate count; transcript paths stay private.
            errors += 1
    return records, errors


def _root_counts(source: CoworkTranscriptSource, paths: list[Path]) -> list[tuple[Path, int]]:
    return [(root, sum(path.is_relative_to(root) for path in paths)) for root in source.roots]


def _readable_check(
    source: CoworkTranscriptSource,
    paths: list[Path],
    records: dict[Path, list[str]],
    errors: int,
    fingerprints: _Fingerprints,
) -> _Check:
    status = _Status.PASS
    if errors:
        status = _Status.FAIL
    elif not source.roots or not paths or not fingerprints.messages:
        status = _Status.WARN
    return _Check(
        "Readable",
        status,
        (
            ("readable sessions", f"{len(records)} / {len(paths)}"),
            ("unreadable sessions", errors),
            ("normalized records", sum(len(items) for items in records.values())),
            ("normalized messages", fingerprints.messages),
        ),
    )


def _separation_check(
    code: ClaudeCodeTranscriptSource,
    cowork: CoworkTranscriptSource,
    code_paths: list[Path],
    cowork_paths: list[Path],
    code_errors: int,
    cowork_errors: int,
    code_fingerprints: _Fingerprints,
    cowork_fingerprints: _Fingerprints,
) -> _Check:
    code_sessions = {code.session_id(path) for path in code_paths}
    cowork_sessions = {cowork.session_id(path) for path in cowork_paths}
    session_overlap = len(code_sessions & cowork_sessions)
    message_overlap = len(code_fingerprints.values & cowork_fingerprints.values)

    status = _Status.PASS
    if code_errors or cowork_errors:
        status = _Status.FAIL
    elif (
        not code_paths
        or not cowork_paths
        or not code_fingerprints.messages
        or not cowork_fingerprints.messages
        or code_fingerprints.skipped
        or cowork_fingerprints.skipped
        or session_overlap
        or message_overlap
    ):
        status = _Status.WARN

    return _Check(
        "Separation",
        status,
        (
            ("Claude Code files", len(code_paths)),
            ("Claude Code session IDs", len(code_sessions)),
            ("Cowork session IDs", len(cowork_sessions)),
            ("session-ID intersection", session_overlap),
            ("Claude Code messages", code_fingerprints.messages),
            ("Cowork messages", cowork_fingerprints.messages),
            ("unfingerprintable messages", code_fingerprints.skipped + cowork_fingerprints.skipped),
            ("exact message overlap", message_overlap),
        ),
    )


def _timeline_check(
    source: ClaudeDesktopTranscriptSource,
    code_paths: list[Path],
    cowork_paths: list[Path],
    roots: tuple[Path, ...],
) -> _Check:
    try:
        composite = source.discover()
        resolved = [path.resolve() for path in composite]
        mtimes = [path.stat().st_mtime_ns for path in composite]
    except Exception:
        return _Check(
            "File timeline",
            _Status.FAIL,
            (
                ("composite files", "unavailable"),
                ("count additive", "unverified"),
                ("paths unique", "unverified"),
                ("mtime order", "unverified"),
                ("Code/Cowork transitions", "unverified"),
            ),
        )

    additive = len(composite) == len(code_paths) + len(cowork_paths)
    unique = len(set(resolved)) == len(resolved)
    ordered = all(left >= right for left, right in pairwise(mtimes))
    labels = ["cowork" if any(path.is_relative_to(root) for root in roots) else "code" for path in composite]
    transitions = sum(left != right for left, right in pairwise(labels))
    status = _Status.PASS if additive and unique and ordered else _Status.FAIL
    if status is _Status.PASS and not composite:
        status = _Status.WARN
    return _Check(
        "File timeline",
        status,
        (
            ("composite files", f"{len(composite)} = {len(code_paths)} + {len(cowork_paths)}"),
            ("count additive", "yes" if additive else "no"),
            ("paths unique", "yes" if unique else "no"),
            ("mtime order", "non-increasing" if ordered else "invalid"),
            ("Code/Cowork transitions", transitions),
        ),
    )


def _render(
    *,
    mode: str,
    cowork: CoworkTranscriptSource,
    cowork_paths: list[Path],
    checks: tuple[_Check, ...],
) -> None:
    print("Cowork verification\n")
    print("Discovery")
    print(f"  {'platform':<27}{sys.platform}")
    print(f"  {'mode':<27}{mode}")
    print(f"  {'roots':<27}{len(cowork.roots)}")
    for root, count in _root_counts(cowork, cowork_paths):
        print(f"  root {root} ({count} session(s))")
    print(f"  {'Cowork sessions':<27}{len(cowork_paths)}")

    for check in checks:
        print(f"\n[{check.status.name}] {check.name}")
        for label, value in check.rows:
            print(f"  {label:<27}{value}")

    result = max((check.status for check in checks), default=_Status.WARN)
    print(f"\nRESULT {result.name}")


async def _cmd_verify(args: argparse.Namespace) -> int:
    mode = "explicit" if args.root is not None else "automatic"
    try:
        cowork = CoworkTranscriptSource(args.root)
        code = ClaudeCodeTranscriptSource(SESSION_DIR)
        composite = ClaudeDesktopTranscriptSource(SESSION_DIR, list(cowork.roots))
        cowork_paths = cowork.discover()
        code_paths = code.discover()
    except Exception as exc:
        print(f"error: Cowork discovery could not complete ({type(exc).__name__})", file=sys.stderr)
        return 1

    try:
        cowork_records, cowork_errors = _read_all(cowork, cowork_paths)
        code_records, code_errors = _read_all(code, code_paths)
        cowork_fingerprints = _fingerprints(cowork, cowork_records)
        code_fingerprints = _fingerprints(code, code_records)
        checks = (
            _readable_check(cowork, cowork_paths, cowork_records, cowork_errors, cowork_fingerprints),
            _separation_check(
                code,
                cowork,
                code_paths,
                cowork_paths,
                code_errors,
                cowork_errors,
                code_fingerprints,
                cowork_fingerprints,
            ),
            _timeline_check(composite, code_paths, cowork_paths, cowork.roots),
        )
        _render(mode=mode, cowork=cowork, cowork_paths=cowork_paths, checks=checks)
    except Exception as exc:
        print(f"error: Cowork verification could not complete ({type(exc).__name__})", file=sys.stderr)
        return 1
    return 1 if any(check.status is _Status.FAIL for check in checks) else 0


def register(sub: Any) -> None:
    cowork = sub.add_parser("cowork", help="Inspect the read-only Cowork and Claude Code transcript sources")
    actions = cowork.add_subparsers(dest="cowork_action", required=True)
    verify = actions.add_parser("verify", help="Verify Cowork readability, source separation, and file timeline")
    verify.add_argument(
        "--root",
        action="append",
        type=_directory,
        help="Claude Desktop data root to probe instead of automatic discovery (repeatable)",
    )
    verify.set_defaults(handler=_cmd_verify)
