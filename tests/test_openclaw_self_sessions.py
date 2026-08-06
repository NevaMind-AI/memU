"""OpenClaw's scheduled bridging run must not mine its own transcript."""

from __future__ import annotations

import pathlib
from argparse import Namespace
from dataclasses import replace

import pytest

from memu.hosts import host_cli
from memu.hosts.bridging import self_sessions
from memu.hosts.bridging.layout import Layout
from memu.hosts.openclaw.cli import SESSION_ID_ENV
from memu.hosts.openclaw.cli import SPEC as OPENCLAW_SPEC
from memu.hosts.openclaw.sessions import OpenClawTranscriptSource


def test_openclaw_declares_the_bridging_session_id_variable() -> None:
    assert OPENCLAW_SPEC.session_id_env == SESSION_ID_ENV == "MEMU_BRIDGING_SESSION_ID"


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("a83c9e20-072d-4708-902a-47c596b14d55.jsonl", "a83c9e20-072d-4708-902a-47c596b14d55"),
        (
            "a83c9e20-072d-4708-902a-47c596b14d55-topic-42.jsonl",
            "a83c9e20-072d-4708-902a-47c596b14d55",
        ),
    ],
)
def test_openclaw_transcript_name_maps_to_its_session_id(filename: str, expected: str, tmp_path: pathlib.Path) -> None:
    transcript = tmp_path / "main" / "sessions" / filename

    assert OpenClawTranscriptSource(tmp_path).session_id(transcript) == expected


@pytest.mark.parametrize("marked", [False, True])
async def test_only_a_marked_openclaw_run_claims_its_session(
    marked: bool, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    session_id = "a83c9e20-072d-4708-902a-47c596b14d55"
    captured: dict[str, object] = {}

    class ExistingOpenClawSource(OpenClawTranscriptSource):
        def exists(self) -> bool:
            return True

    spec = replace(OPENCLAW_SPEC, source_factory=ExistingOpenClawSource)

    async def fake_prepare(*args: object, **kwargs: object) -> int:
        captured["skip_sessions"] = kwargs["skip_sessions"]
        return 0

    monkeypatch.setattr(host_cli, "prepare", fake_prepare)
    monkeypatch.setattr(host_cli, "_refresh_retrieval", lambda spec: None)
    monkeypatch.setattr(host_cli.events, "flush", lambda: None)
    monkeypatch.setattr(host_cli.Path, "cwd", lambda: tmp_path / "project")
    monkeypatch.setenv(SESSION_ID_ENV, session_id)
    if marked:
        monkeypatch.setenv(self_sessions.BRIDGING_RUN_ENV, "1")
    else:
        monkeypatch.delenv(self_sessions.BRIDGING_RUN_ENV, raising=False)

    base = tmp_path / "memu-openclaw"
    rc = await host_cli._cmd_prepare(
        spec,
        Namespace(session_dir=str(tmp_path / "agents"), base_dir=str(base), max_jobs=10),
    )

    expected = [session_id] if marked else []
    assert rc == 0
    assert captured["skip_sessions"] == expected
    assert self_sessions.load(Layout(base=base, host="openclaw").self_sessions) == expected


def test_openclaw_scheduled_prompt_captures_and_exports_the_session_id() -> None:
    doc = (pathlib.Path(__file__).resolve().parents[1] / "src/memu/hosts/openclaw/BRIDGING_TASK.md").read_text(
        encoding="utf-8"
    )

    status = doc.index("session_status")
    prepare = doc.index(f"{self_sessions.BRIDGING_RUN_ENV}=1 {SESSION_ID_ENV}='<sessionId>' memu-openclaw prepare")

    assert status < prepare
    assert ":run:<sessionId>" in doc
