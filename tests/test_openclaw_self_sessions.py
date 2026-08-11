"""OpenClaw's memU cron job is identified from scheduler-owned session metadata."""

from __future__ import annotations

import json
import pathlib
import sqlite3
from argparse import Namespace
from dataclasses import replace

import pytest

from memu.hosts import host_cli
from memu.hosts.bridging.layout import Layout
from memu.hosts.bridging.self_sessions import load as load_self_sessions
from memu.hosts.openclaw import cron_identity
from memu.hosts.openclaw.cli import SPEC as OPENCLAW_SPEC
from memu.hosts.openclaw.sessions import OpenClawTranscriptSource


def _store(root: pathlib.Path, agent_id: str, rows: list[tuple[str, str]]) -> pathlib.Path:
    db = root / agent_id / "agent" / "openclaw-agent.sqlite"
    db.parent.mkdir(parents=True)
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE session_windows (
          session_id TEXT PRIMARY KEY,
          session_key TEXT NOT NULL
        ) STRICT;
        """
    )
    conn.executemany("INSERT INTO session_windows (session_id, session_key) VALUES (?, ?)", rows)
    conn.commit()
    conn.close()
    return db


def test_registration_round_trips_without_putting_identity_in_the_cron_prompt(tmp_path: pathlib.Path) -> None:
    path = cron_identity.registration_path(tmp_path)

    cron_identity.save_registration(path, agent_id="main", job_id="job-123")

    assert cron_identity.load_registration(path) == cron_identity.CronRegistration(agent_id="main", job_id="job-123")
    assert json.loads(path.read_text(encoding="utf-8")) == {"agent_id": "main", "job_id": "job-123"}


def test_register_cron_job_cli_writes_the_prepare_registration(tmp_path: pathlib.Path) -> None:
    assert OPENCLAW_SPEC.binary == "memu-openclaw"
    assert (
        host_cli.run(
            OPENCLAW_SPEC,
            [
                "register-cron-job",
                "--job-id",
                "job-123",
                "--agent-id",
                "worker",
                "--base-dir",
                str(tmp_path),
            ],
        )
        == 0
    )

    assert cron_identity.load_registration(cron_identity.registration_path(tmp_path)) == (
        cron_identity.CronRegistration(agent_id="worker", job_id="job-123")
    )


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("agent_id", "bad:value"),
        ("job_id", "bad:value"),
        ("agent_id", "../other"),
        ("job_id", "job/other"),
        ("agent_id", ""),
    ],
)
def test_registration_rejects_invalid_session_key_segments(field: str, invalid: str, tmp_path: pathlib.Path) -> None:
    values = {"agent_id": "main", "job_id": "job-123"}
    values[field] = invalid

    with pytest.raises(ValueError, match=field):
        cron_identity.save_registration(cron_identity.registration_path(tmp_path), **values)


def test_missing_registration_fails_open_to_existing_self_sessions(tmp_path: pathlib.Path) -> None:
    layout = Layout(base=tmp_path / "memu-openclaw", host="openclaw")
    layout.self_sessions.parent.mkdir(parents=True)
    layout.self_sessions.write_text('["already-known"]', encoding="utf-8")

    assert cron_identity.resolve_registered_sessions(OpenClawTranscriptSource(tmp_path / "agents"), layout) == [
        "already-known"
    ]


def test_resolver_selects_every_run_of_only_the_registered_job(tmp_path: pathlib.Path) -> None:
    _store(
        tmp_path,
        "main",
        [
            ("target-1", "agent:main:cron:job-123:run:target-1"),
            ("target-2", "agent:main:cron:job-123:run:target-2"),
            ("control", "agent:main:cron:job-999:run:control"),
            ("forged", "agent:main:cron:job-123:run:not-forged"),
            ("descendant", "agent:main:cron:job-123:run:target-1:subagent:child"),
        ],
    )
    source = OpenClawTranscriptSource(tmp_path)
    registration = cron_identity.CronRegistration(agent_id="main", job_id="job-123")

    assert cron_identity.resolve_session_ids(source, registration) == ["target-1", "target-2"]


def test_resolver_reads_the_registered_agent_store_only(tmp_path: pathlib.Path) -> None:
    _store(tmp_path, "main", [("main-run", "agent:main:cron:job-123:run:main-run")])
    _store(tmp_path, "other", [("other-run", "agent:other:cron:job-123:run:other-run")])
    source = OpenClawTranscriptSource(tmp_path)

    assert cron_identity.resolve_session_ids(
        source, cron_identity.CronRegistration(agent_id="other", job_id="job-123")
    ) == ["other-run"]


async def test_prepare_remembers_structurally_resolved_sessions_without_launch_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    captured: dict[str, object] = {}
    base = tmp_path / "memu-openclaw"
    registration = cron_identity.CronRegistration(agent_id="main", job_id="job-123")
    cron_identity.save_registration(cron_identity.registration_path(base), **registration.__dict__)

    class ExistingOpenClawSource(OpenClawTranscriptSource):
        def exists(self) -> bool:
            return True

    async def fake_prepare(*args: object, **kwargs: object) -> int:
        captured["skip_sessions"] = kwargs["skip_sessions"]
        return 0

    monkeypatch.setattr(host_cli, "prepare", fake_prepare)
    monkeypatch.setattr(host_cli, "_refresh_retrieval", lambda spec: None)
    monkeypatch.setattr(host_cli.events, "flush", lambda: None)
    monkeypatch.setattr(cron_identity, "resolve_session_ids", lambda source, registration: ["run-1", "run-2"])

    spec = replace(OPENCLAW_SPEC, source_factory=ExistingOpenClawSource)
    rc = await host_cli._cmd_prepare(
        spec,
        Namespace(session_dir=str(tmp_path / "agents"), base_dir=str(base), max_jobs=10),
    )

    assert rc == 0
    assert captured["skip_sessions"] == ["run-1", "run-2"]
    assert load_self_sessions(Layout(base=base, host="openclaw").self_sessions) == ["run-1", "run-2"]


def test_openclaw_scheduled_prompt_registers_job_once_and_carries_no_session_identity() -> None:
    doc = (pathlib.Path(__file__).resolve().parents[1] / "src/memu/hosts/openclaw/BRIDGING_TASK.md").read_text(
        encoding="utf-8"
    )
    prompt = doc[doc.index("```\nRun the memU bridging pipeline") : doc.index("\n```", doc.index("```\nRun"))]

    assert "memu-openclaw register-cron-job" in doc
    assert "memu-openclaw prepare" in prompt
    assert "session_status" not in prompt
    assert "MEMU_BRIDGING_SESSION_ID" not in doc
    assert "MEMU_BRIDGING_RUN" not in prompt
    assert ":run:<sessionId>" not in prompt


def test_openclaw_scheduled_task_uses_an_isolated_turn_and_portable_path_checks() -> None:
    doc = (pathlib.Path(__file__).resolve().parents[1] / "src/memu/hosts/openclaw/BRIDGING_TASK.md").read_text(
        encoding="utf-8"
    )

    assert 'sessionTarget="isolated"' in doc
    assert "command -v memu-openclaw" in doc
    assert "Get-Command memu-openclaw" in doc
    assert "env -i PATH=/usr/bin:/bin /bin/sh" not in doc
