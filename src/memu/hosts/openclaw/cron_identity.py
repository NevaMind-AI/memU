"""Persist and resolve the OpenClaw cron job that owns bridging runs."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from memu.hosts.base import TranscriptSource
from memu.hosts.bridging import self_sessions
from memu.hosts.bridging.layout import Layout
from memu.hosts.openclaw.sessions import OpenClawTranscriptSource

logger = logging.getLogger(__name__)

_REGISTRATION_FILE = ".cron_job.openclaw.json"


@dataclass(frozen=True)
class CronRegistration:
    agent_id: str
    job_id: str


class InvalidCronRegistration(ValueError):
    def __init__(self, field: str) -> None:
        super().__init__(f"{field} must contain only letters, digits, '.', '_', or '-'")


def _session_key_segment(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise InvalidCronRegistration(name)
    value = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]+", value):
        raise InvalidCronRegistration(name)
    return value


def registration_path(base: str | Path) -> Path:
    return Path(base).expanduser() / _REGISTRATION_FILE


def save_registration(path: Path, *, agent_id: str, job_id: str) -> CronRegistration:
    registration = CronRegistration(
        agent_id=_session_key_segment("agent_id", agent_id),
        job_id=_session_key_segment("job_id", job_id),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"agent_id": registration.agent_id, "job_id": registration.job_id}, indent=2),
        encoding="utf-8",
    )
    return registration


def load_registration(path: Path) -> CronRegistration | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            return None
        return CronRegistration(
            agent_id=_session_key_segment("agent_id", value.get("agent_id", "")),
            job_id=_session_key_segment("job_id", value.get("job_id", "")),
        )
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def resolve_session_ids(source: OpenClawTranscriptSource, registration: CronRegistration) -> list[str]:
    """Return every exact run session owned by the registered cron job."""
    return source.cron_run_session_ids(agent_id=registration.agent_id, job_id=registration.job_id)


def _remember_all(path: Path, session_ids: list[str]) -> list[str]:
    """Persist every structural id; OpenClaw archives can outlive active rows."""
    remembered = self_sessions.load(path)
    merged = list(dict.fromkeys([*remembered, *session_ids]))
    if merged != remembered:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return merged


def resolve_registered_sessions(source: TranscriptSource, layout: Layout) -> list[str]:
    """Remember registered OpenClaw cron runs and return the complete skip set."""
    remembered = self_sessions.load(layout.self_sessions)
    registration = load_registration(registration_path(layout.base))
    if registration is None:
        logger.warning(
            "no OpenClaw bridging cron job is registered; run "
            "`memu-openclaw register-cron-job --job-id <jobId> --agent-id <agentId>` "
            "or this run's transcript cannot be excluded"
        )
        return remembered
    if not isinstance(source, OpenClawTranscriptSource):
        return remembered
    resolved = resolve_session_ids(source, registration)
    if not resolved:
        logger.warning(
            "no sessions matched registered OpenClaw cron job %s for agent %s; "
            "this run's transcript cannot be excluded",
            registration.job_id,
            registration.agent_id,
        )
    return _remember_all(layout.self_sessions, resolved)
