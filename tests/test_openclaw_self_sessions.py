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


def test_registration_round_trips_only_the_stable_job_identity(tmp_path: pathlib.Path) -> None:
    path = cron_identity.registration_path(tmp_path)

    cron_identity.save_registration(path, job_id="job-123")

    assert cron_identity.load_registration(path) == cron_identity.CronRegistration(job_id="job-123")
    assert json.loads(path.read_text(encoding="utf-8")) == {"job_id": "job-123"}


def test_registration_loads_the_intermediate_job_and_agent_format(tmp_path: pathlib.Path) -> None:
    path = cron_identity.registration_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"agent_id":"main","job_id":"job-123"}', encoding="utf-8")

    assert cron_identity.load_registration(path) == cron_identity.CronRegistration(job_id="job-123")


def test_register_cron_job_cli_writes_the_prepare_registration(tmp_path: pathlib.Path) -> None:
    assert OPENCLAW_SPEC.binary == "memu-openclaw"
    assert (
        host_cli.run(
            OPENCLAW_SPEC,
            [
                "register-cron-job",
                "--job-id",
                "job-123",
                "--base-dir",
                str(tmp_path),
            ],
        )
        == 0
    )

    assert cron_identity.load_registration(cron_identity.registration_path(tmp_path)) == (
        cron_identity.CronRegistration(job_id="job-123")
    )


@pytest.mark.parametrize("invalid", ["bad:value", "job/other", ""])
def test_registration_rejects_invalid_job_ids(invalid: str, tmp_path: pathlib.Path) -> None:
    with pytest.raises(ValueError, match="job_id"):
        cron_identity.save_registration(cron_identity.registration_path(tmp_path), job_id=invalid)


def test_missing_registration_warns_only_after_structural_capability_is_available(
    caplog: pytest.LogCaptureFixture, tmp_path: pathlib.Path
) -> None:
    layout = Layout(base=tmp_path / "memu-openclaw", host="openclaw")
    layout.self_sessions.parent.mkdir(parents=True)
    layout.self_sessions.write_text('["already-known"]', encoding="utf-8")
    _store(tmp_path / "agents", "main", [])
    source = OpenClawTranscriptSource(tmp_path / "agents")

    assert cron_identity.resolve_registered_sessions(source, layout) == ["already-known"]
    assert cron_identity.resolve_registered_sessions(source, layout) == ["already-known"]

    assert caplog.text.count("no OpenClaw bridging cron job is registered") == 1


def test_unreadable_agent_database_emits_only_the_deduplicated_compatibility_warning(
    caplog: pytest.LogCaptureFixture, tmp_path: pathlib.Path
) -> None:
    layout = Layout(base=tmp_path / "memu-openclaw", host="openclaw")
    db = tmp_path / "agents" / "main" / "agent" / "openclaw-agent.sqlite"
    db.parent.mkdir(parents=True)
    db.write_text("not a database", encoding="utf-8")
    source = OpenClawTranscriptSource(tmp_path / "agents")

    assert cron_identity.resolve_registered_sessions(source, layout) == []
    assert cron_identity.resolve_registered_sessions(source, layout) == []

    assert caplog.text.count("requires OpenClaw v2026.7.2-beta.4 or newer") == 1
    assert "could not inspect OpenClaw session schema" not in caplog.text


def test_legacy_agent_database_without_session_windows_warns_once_and_fails_open(
    caplog: pytest.LogCaptureFixture, tmp_path: pathlib.Path
) -> None:
    layout = Layout(base=tmp_path / "memu-openclaw", host="openclaw")
    layout.self_sessions.parent.mkdir(parents=True)
    layout.self_sessions.write_text('["already-known"]', encoding="utf-8")
    db = tmp_path / "agents" / "main" / "agent" / "openclaw-agent.sqlite"
    db.parent.mkdir(parents=True)
    sqlite3.connect(db).close()
    source = OpenClawTranscriptSource(tmp_path / "agents")

    assert cron_identity.resolve_registered_sessions(source, layout) == ["already-known"]
    assert cron_identity.resolve_registered_sessions(source, layout) == ["already-known"]

    assert caplog.text.count("requires OpenClaw v2026.7.2-beta.4 or newer") == 1
    assert "no OpenClaw bridging cron job is registered" not in caplog.text


def test_unsupported_openclaw_store_warns_once_then_warns_again_after_recovery(
    caplog: pytest.LogCaptureFixture, tmp_path: pathlib.Path
) -> None:
    layout = Layout(base=tmp_path / "memu-openclaw", host="openclaw")
    registration = cron_identity.CronRegistration(job_id="job-123")
    cron_identity.save_registration(cron_identity.registration_path(layout.base), **registration.__dict__)
    source = OpenClawTranscriptSource(tmp_path / "agents")

    cron_identity.resolve_registered_sessions(source, layout)
    cron_identity.resolve_registered_sessions(source, layout)
    assert caplog.text.count("requires OpenClaw v2026.7.2-beta.4 or newer") == 1

    _store(tmp_path / "agents", "main", [("run-1", "agent:main:cron:job-123:run:run-1")])
    assert cron_identity.resolve_registered_sessions(source, layout) == ["run-1"]

    (tmp_path / "agents" / "main" / "agent" / "openclaw-agent.sqlite").unlink()
    cron_identity.resolve_registered_sessions(source, layout)
    assert caplog.text.count("requires OpenClaw v2026.7.2-beta.4 or newer") == 2


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
    registration = cron_identity.CronRegistration(job_id="job-123")

    assert cron_identity.resolve_session_ids(source, registration) == ["main/target-1", "main/target-2"]


def test_structural_sessions_are_remembered_beyond_the_shared_launch_env_limit(tmp_path: pathlib.Path) -> None:
    layout = Layout(base=tmp_path / "memu-openclaw", host="openclaw")
    registration = cron_identity.CronRegistration(job_id="job-123")
    cron_identity.save_registration(cron_identity.registration_path(layout.base), **registration.__dict__)
    _store(tmp_path / "agents", "main", [])
    source = OpenClawTranscriptSource(tmp_path / "agents")
    expected = [f"run-{index:04d}" for index in range(1001)]

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(cron_identity, "resolve_session_ids", lambda source, registration: expected)
        assert cron_identity.resolve_registered_sessions(source, layout) == expected

    assert load_self_sessions(layout.self_sessions) == expected


def test_resolver_follows_one_job_across_agent_owner_changes(tmp_path: pathlib.Path) -> None:
    _store(tmp_path, "main", [("main-run", "agent:main:cron:job-123:run:main-run")])
    _store(tmp_path, "other", [("other-run", "agent:other:cron:job-123:run:other-run")])
    _store(tmp_path, "control", [("control-run", "agent:control:cron:job-999:run:control-run")])
    source = OpenClawTranscriptSource(tmp_path)

    assert cron_identity.resolve_session_ids(source, cron_identity.CronRegistration(job_id="job-123")) == [
        "main/main-run",
        "other/other-run",
    ]


def test_resolver_silently_skips_legacy_agent_stores_in_a_mixed_install(
    caplog: pytest.LogCaptureFixture, tmp_path: pathlib.Path
) -> None:
    legacy = tmp_path / "legacy" / "agent" / "openclaw-agent.sqlite"
    legacy.parent.mkdir(parents=True)
    sqlite3.connect(legacy).close()
    _store(tmp_path, "current", [("run-1", "agent:current:cron:job-123:run:run-1")])
    source = OpenClawTranscriptSource(tmp_path)

    assert cron_identity.resolve_session_ids(source, cron_identity.CronRegistration(job_id="job-123")) == [
        "current/run-1"
    ]
    assert "no such table: session_windows" not in caplog.text


async def test_legacy_jsonl_prepare_still_creates_jobs_after_capability_warning(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    session = tmp_path / "agents" / "main" / "sessions" / "legacy-run.jsonl"
    session.parent.mkdir(parents=True)
    session.write_text(
        "\n".join([
            json.dumps({"type": "message", "message": {"role": "user", "content": "remember this"}}),
            json.dumps({"type": "message", "message": {"role": "assistant", "content": "noted"}}),
        ])
        + "\n",
        encoding="utf-8",
    )

    class EmptyRecallService:
        async def list_all_recall_files(self, *args: object, **kwargs: object) -> dict[str, object]:
            return {"recall_files": [], "next_cursor": None}

    from memu.hosts.bridging import pipeline

    monkeypatch.setattr(pipeline, "build_agentic_memory_backend_from_env", lambda: EmptyRecallService())
    monkeypatch.setattr(host_cli, "_refresh_retrieval", lambda spec: None)
    monkeypatch.setattr(host_cli.events, "flush", lambda: None)
    base = tmp_path / "memu-openclaw"

    rc = await host_cli._cmd_prepare(
        OPENCLAW_SPEC,
        Namespace(session_dir=str(tmp_path / "agents"), base_dir=str(base), max_jobs=10),
    )

    assert rc == 0
    assert sorted(path.name for path in (base / "jobs").glob("*.txt")) == ["1.txt", "2.txt", "3.txt"]
    assert caplog.text.count("requires OpenClaw v2026.7.2-beta.4 or newer") == 1


async def test_prepare_remembers_structurally_resolved_sessions_without_launch_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    captured: dict[str, object] = {}
    base = tmp_path / "memu-openclaw"
    registration = cron_identity.CronRegistration(job_id="job-123")
    cron_identity.save_registration(cron_identity.registration_path(base), **registration.__dict__)

    class ExistingOpenClawSource(OpenClawTranscriptSource):
        def exists(self) -> bool:
            return True

        def supports_cron_run_identity(self) -> bool:
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


def test_topic_like_legacy_filename_keeps_its_exact_session_id(tmp_path: pathlib.Path) -> None:
    session = tmp_path / "main" / "sessions" / "real-topic-42.jsonl"

    assert OpenClawTranscriptSource(tmp_path).session_id(session) == "main/real-topic-42"


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


def test_openclaw_scheduled_task_keeps_legacy_installs_non_blocking() -> None:
    doc = (pathlib.Path(__file__).resolve().parents[1] / "src/memu/hosts/openclaw/BRIDGING_TASK.md").read_text(
        encoding="utf-8"
    )
    compatibility = doc[doc.index("## Compatibility behavior") : doc.index("## Step 0")]

    assert "v2026.7.2-beta.4" in compatibility
    assert "session_windows" in compatibility
    assert "session_id + session_key" in compatibility
    assert "schema capability" in compatibility
    assert "warn once, non-blocking" in compatibility
    assert "continue PREPARE -> SELF-EVOLVE -> COMMIT unchanged" in compatibility
    assert "Upgrading to a prerelease is optional" in compatibility
    assert "v2026.7.2-beta.1" not in doc


def test_openclaw_task_documents_precise_verification_for_both_capabilities() -> None:
    doc = (pathlib.Path(__file__).resolve().parents[1] / "src/memu/hosts/openclaw/BRIDGING_TASK.md").read_text(
        encoding="utf-8"
    )

    assert "Every version:" in doc
    assert "Structural schema:" in doc
    assert "Legacy schema:" in doc
    assert ".self_sessions.openclaw.json" in doc
    assert ".session_manifest.openclaw.json.pending" in doc
    assert "session ID from that triggered run's scheduler result" in doc
    assert "ordinary JSONL sessions still produce jobs" in doc
    assert "tool result must show `memu-openclaw prepare`" in doc


def test_openclaw_task_reuses_one_existing_bridging_job_before_creation() -> None:
    doc = (pathlib.Path(__file__).resolve().parents[1] / "src/memu/hosts/openclaw/BRIDGING_TASK.md").read_text(
        encoding="utf-8"
    )
    step0 = doc[doc.index("## Step 0") : doc.index("## Step 1")]
    prose = " ".join(step0.split())
    creation = doc.index("## Step 2 — create or update and register the cron job")

    assert doc.index("## Step 0") < creation
    for signal in ("memu-openclaw prepare", "memu-openclaw commit", "~/.memu/hosts/openclaw/jobs/"):
        assert signal in step0
    assert "all three signals" in prose
    assert "one or two signals" in prose
    assert "absolute executable or jobs path" in prose
    assert "name resembles a memU bridging task" in prose
    assert "zero unresolved near matches" in prose
    assert "Exactly one candidate" in prose
    assert "No candidate or near match" in prose
    assert "Multiple candidates or any near match" in prose
    for preserved in ("job ID", "schedule", "name", "enabled state", "owner", "delivery", "unrelated payload settings"):
        assert preserved in prose
    assert "show the in-place patch and confirm" in prose
    assert "stop without creating, deleting, updating, registering, or guessing" in prose
    doc_prose = " ".join(doc.split())
    assert "register that exact selected job ID" in doc_prose
    assert "--job-id <jobId>" in doc
    assert "--agent-id" not in doc
    assert "Do not persist the job's current agent or model" in doc_prose


def test_openclaw_task_preserves_execution_order_and_failure_boundaries() -> None:
    doc = (pathlib.Path(__file__).resolve().parents[1] / "src/memu/hosts/openclaw/BRIDGING_TASK.md").read_text(
        encoding="utf-8"
    )
    prompt_start = doc.index("```\nRun the memU bridging pipeline")
    prompt_end = doc.index("\n```", prompt_start)
    prompt = doc[prompt_start:prompt_end]

    assert doc.index('sessionTarget="isolated"') < doc.index("memu-openclaw register-cron-job") < prompt_start
    prompt_prose = " ".join(prompt.split())
    assert "sort by each filename's integer stem" in prompt_prose
    assert "If this leftovers commit exits non-zero, stop" in prompt_prose
    assert "If any PREPARE or COMMIT command exited non-zero" in prompt_prose
    assert "memu-openclaw register-cron-job" not in prompt
    assert "session_status" not in prompt
