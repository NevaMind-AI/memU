"""Client event reporting (ADR 0016).

Weighted toward the two properties that matter more than delivery: **nothing
leaks**, and **nothing breaks**. A telemetry module that loses events is a
disappointment; one that ships a user's memory content, or that turns a working
``retrieve`` into a failed one, is a defect of a different kind.
"""

from __future__ import annotations

import json
import pathlib
import urllib.error
from typing import Any

import pytest

from memu import events
from memu.hosts.claude_code.cli import SPEC as CLAUDE_SPEC
from memu.hosts.codex.cli import SPEC as CODEX_SPEC
from memu.hosts.host_cli import run


@pytest.fixture
def reporting(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> pathlib.Path:
    """Reporting on, pointed at a spool under ``tmp_path``. Returns the spool."""
    from memu import env as env_module

    spool = tmp_path / "events.jsonl"
    monkeypatch.setenv("MEMU_EVENTS_BASE_URL", "https://example.invalid/events")
    monkeypatch.setenv("MEMU_EVENTS_SPOOL", str(spool))
    monkeypatch.setenv("MEMU_CONFIG_ENV", str(tmp_path / "config.env"))
    monkeypatch.setenv("MEMU_MEMORY_MODE", "local")
    monkeypatch.delenv("DO_NOT_TRACK", raising=False)
    monkeypatch.delenv("MEMU_TELEMETRY", raising=False)
    monkeypatch.delenv("MEMU_CLOUD_API_KEY", raising=False)
    # The dotenv loader is process-cached, so a previous test's config file would
    # otherwise leak in — including its MEMU_CLIENT_ID.
    env_module.reload()
    return spool


def _spooled(spool: pathlib.Path) -> list[dict[str, Any]]:
    if not spool.is_file():
        return []
    return [json.loads(line) for line in spool.read_text(encoding="utf-8").splitlines() if line.strip()]


class _Posted:
    """Stands in for the endpoint, capturing what was sent."""

    def __init__(self, status: int = 200, error: Exception | None = None) -> None:
        self.status = status
        self.error = error
        # One envelope per request, never a list: the endpoint validates the body
        # as a single object, so a body that is not a dict is itself the failure.
        self.events: list[dict[str, Any]] = []
        self.headers: list[dict[str, str]] = []

    def __call__(self, request: Any, timeout: float | None = None) -> Any:
        body = json.loads(request.data)
        assert isinstance(body, dict), f"the endpoint takes one event per POST, got {type(body).__name__}"
        self.events.append(body)
        self.headers.append(dict(request.headers))
        if self.error is not None:
            raise self.error
        return _Response(self.status)


class _Response:
    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


# --------------------------------------------------------------------------- #
# The envelope
# --------------------------------------------------------------------------- #


def test_envelope_carries_every_field_the_backend_expects(reporting: pathlib.Path) -> None:
    events.record(events.CLI_INSTALL_COMPLETED, host="claude-code")

    (event,) = _spooled(reporting)
    assert set(event) >= {
        "event_id",
        "event_name",
        "client_type",
        "client_instance_id",
        "client_version",
        "agent_platform",
        "os",
        "deployment_mode",
        "occurred_at",
        "context",
        "properties",
    }
    assert event["client_type"] == "memu_cli"
    assert event["deployment_mode"] == "local"
    assert event["occurred_at"].endswith("Z")


def test_event_ids_are_unique_so_a_retry_can_be_deduplicated(reporting: pathlib.Path) -> None:
    events.record(events.CLI_INSTALL_COMPLETED, host="codex")
    events.record(events.CLI_INSTALL_COMPLETED, host="codex")

    ids = {event["event_id"] for event in _spooled(reporting)}
    assert len(ids) == 2


def test_agent_platform_is_normalised_not_passed_through(reporting: pathlib.Path) -> None:
    # `claude-code` is also the on-disk directory name, so the mapping has to
    # happen here rather than by renaming the host.
    assert events.agent_platform("claude-code") == "claude_code"
    # The generic adapter's host id is `agent`; "agent" is meaningless as a
    # platform dimension.
    assert events.agent_platform("agent") == "generic"
    assert events.agent_platform("codex") == "codex"
    # The core `memu` binary has no host at all.
    assert events.agent_platform("") == "none"


def test_session_id_is_omitted_rather_than_faked(reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    events.record(events.CLI_INSTALL_COMPLETED, host="claude-code", session_id_env="CLAUDE_CODE_SESSION_ID")
    (absent,) = _spooled(reporting)
    assert "session_id" not in absent

    reporting.unlink()
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "abc-123")
    events.record(events.CLI_INSTALL_COMPLETED, host="claude-code", session_id_env="CLAUDE_CODE_SESSION_ID")
    (present,) = _spooled(reporting)
    assert present["session_id"] == "abc-123"


def test_client_instance_id_persists_in_config_and_survives_a_reinstall(
    reporting: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    from memu import env as env_module

    events.record(events.CLI_INSTALL_COMPLETED, host="codex")
    first = _spooled(reporting)[0]["client_instance_id"]

    # `UNINSTALL.md` Part 3 keeps config.env unconditionally, which is the whole
    # reason the id lives there: install -> uninstall -> reinstall stays one
    # instance's history.
    assert f"MEMU_CLIENT_ID={first}" in (tmp_path / "config.env").read_text(encoding="utf-8")

    env_module.reload()
    reporting.unlink()
    events.record(events.CLI_UNINSTALLED, host="codex")
    assert _spooled(reporting)[0]["client_instance_id"] == first


# --------------------------------------------------------------------------- #
# Nothing leaks
# --------------------------------------------------------------------------- #


def test_properties_are_an_allowlist_not_a_passthrough(reporting: pathlib.Path) -> None:
    events.record(
        events.CORE_ACTION_COMPLETED,
        host="codex",
        properties={
            "action_name": "memory_search",
            "result_count": 3,
            # Everything below is exactly what must never leave the machine.
            "query": "what did I tell you about my salary",
            "store_dsn": "postgres://user:pw@host/db",
            "path": "/Users/someone/secret-project/notes.md",
        },
    )

    (event,) = _spooled(reporting)
    assert event["properties"] == {"action_name": "memory_search", "result_count": 3}


def test_success_only_events_carry_no_properties(reporting: pathlib.Path) -> None:
    # A constant `success: true` would teach a consumer nothing and invite
    # someone to later send `false`, re-creating the failure channel that the
    # success-only decision removed.
    events.record(events.CLI_INSTALL_COMPLETED, host="codex", properties={"success": True})
    assert _spooled(reporting)[0]["properties"] == {}


_LEAKY_MESSAGE = "connect to postgres://user:hunter2@db.internal/memu failed"


def _raise_leaky() -> None:
    raise RuntimeError(_LEAKY_MESSAGE)


def test_cli_error_reports_modules_and_never_paths_or_messages(reporting: pathlib.Path) -> None:
    try:
        _raise_leaky()
    except RuntimeError as exc:
        events.record_cli_error(exc, command="prepare", host="codex")

    (event,) = _spooled(reporting)
    blob = json.dumps(event)
    assert event["properties"]["error_type"] == "RuntimeError"
    # The message is where DSNs, tokens and home paths actually surface.
    assert "hunter2" not in blob
    assert "postgres://" not in blob
    # Frames are dotted modules, never filesystem paths.
    assert event["properties"]["frames"]
    for frame in event["properties"]["frames"]:
        assert "/" not in frame
        assert "\\" not in frame
    assert any(frame.startswith("tests.") or frame.startswith("<external>") for frame in event["properties"]["frames"])


def test_cli_error_collapses_frames_from_outside_the_package(reporting: pathlib.Path) -> None:
    # A path through the user's own checkout is not safe to report, and telling
    # it apart from site-packages reliably is not worth the risk.
    assert events._module_of("/Users/someone/private/thing.py") == "<external>"
    assert events._module_of("/opt/venv/lib/python3.13/site-packages/memu/hosts/host_cli.py") == "memu.hosts.host_cli"


def test_agent_detail_is_truncated_so_a_transcript_cannot_be_pasted(reporting: pathlib.Path) -> None:
    events.record_agent_error(stage="other", detail="x" * 5000, host="codex")

    (event,) = _spooled(reporting)
    assert len(event["properties"]["detail"]) == events.MAX_DETAIL_CHARS


def test_agent_error_deduplicates_a_retry_loop(reporting: pathlib.Path) -> None:
    for _ in range(5):
        events.record_agent_error(stage="remember", detail="cron never fired", host="codex")
    events.record_agent_error(stage="retrieve", detail="cron never fired", host="codex")

    assert len(_spooled(reporting)) == 2


def test_agent_error_dedup_survives_the_flush_its_own_command_performs(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reason dedup remembers in a sidecar rather than by scanning the spool.

    `report error` flushes inline, so by the time an agent retries, the spool it
    would have been checked against is empty — and every repeat would read as new.
    """
    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    for _ in range(3):
        assert run(CODEX_SPEC, ["report", "error", "--stage", "install", "--detail", "no wheel"]) == 0

    assert len(posted.events) == 1


def test_agent_error_reports_again_once_the_dedup_window_has_passed(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A failure still happening an hour later is a different fact, and worth a row.
    events.record_agent_error(stage="install", detail="no wheel", host="codex")
    monkeypatch.setattr(events, "ERROR_DEDUP_SECONDS", 0.0)
    events.record_agent_error(stage="install", detail="no wheel", host="codex")

    assert len(_spooled(reporting)) == 2


def test_report_error_keeps_the_event_when_the_endpoint_is_unreachable(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # An inline flush that fails costs the wait, never the event: it stays on disk
    # for the next one. Fail-open is the whole reason this verb may flush at all.
    monkeypatch.setattr(events.urllib.request, "urlopen", _Posted(error=OSError("offline")))

    assert run(CODEX_SPEC, ["report", "error", "--stage", "other", "--detail", "offline"]) == 0

    (retained,) = reporting.parent.glob("events.jsonl.*.sending")
    (event,) = _spooled(retained)
    assert event["properties"]["detail"] == "offline"


def test_stage_vocabulary_keeps_its_two_load_bearing_values() -> None:
    # `retrieve`: a retrieval that returns nothing forever throws nothing, so
    # `cli_error` cannot see it and only an agent can report it.
    assert "retrieve" in events.STAGES
    # `other`: a closed enum without an escape hatch turns *unclassifiable* into
    # *unreported*, which is the loss this feature exists to prevent.
    assert "other" in events.STAGES


# --------------------------------------------------------------------------- #
# Nothing breaks
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("variable", "value"),
    [("MEMU_TELEMETRY", "0"), ("DO_NOT_TRACK", "1"), ("MEMU_EVENTS_BASE_URL", "")],
)
def test_each_kill_switch_stops_recording_entirely(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, variable: str, value: str
) -> None:
    monkeypatch.setenv(variable, value)
    events.record(events.CLI_INSTALL_COMPLETED, host="codex")
    events.record_agent_error(stage="other", detail="nope", host="codex")

    assert not reporting.exists()
    assert events.flush() == (0, 0)


def test_recording_survives_an_unwritable_spool(reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMU_EVENTS_SPOOL", "/definitely/not/a/writable/path/events.jsonl")
    events.record(events.CLI_INSTALL_COMPLETED, host="codex")  # must not raise


def test_recording_survives_broken_config(reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # `memory_mode()` raises on this. Reporting must not be what surfaces it.
    monkeypatch.setenv("MEMU_MEMORY_MODE", "nonsense")
    events.record(events.CLI_INSTALL_COMPLETED, host="codex")
    assert not reporting.exists()


def test_flush_survives_an_unreachable_endpoint(reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    events.record(events.CLI_INSTALL_COMPLETED, host="codex")
    monkeypatch.setattr(events.urllib.request, "urlopen", _Posted(error=OSError("no route to host")))

    assert events.flush() == (0, 0)
    # Retained, not lost.
    assert list(reporting.parent.glob("events.jsonl.*.sending"))


def test_a_retrieve_that_cannot_report_is_still_a_successful_retrieve(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The load-bearing guarantee: reporting cannot fail a command.

    ``_cmd_retrieve`` does not guard its own call — the guard lives inside
    ``events``, which is what makes it hold for every call site rather than the
    ones someone remembered to wrap.
    """
    from memu.hosts import retrieval

    async def _fake(query: str, where: Any = None) -> dict[str, Any]:
        return {"segments": [{"text": "hi"}], "files": [], "resources": []}

    def _explode(*args: object, **kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(retrieval, "retrieve", _fake)
    monkeypatch.setattr(events, "envelope", _explode)

    assert run(CODEX_SPEC, ["retrieve", "anything"]) == 0


# --------------------------------------------------------------------------- #
# Delivery
# --------------------------------------------------------------------------- #


def test_flush_posts_each_event_singly_and_clears_the_spool(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events.record(events.CLI_INSTALL_COMPLETED, host="codex")
    events.record(events.CLI_UNINSTALLED, host="codex")
    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    assert events.flush() == (2, 0)
    # Two events, two requests, spool order preserved.
    assert [event["event_name"] for event in posted.events] == [
        events.CLI_INSTALL_COMPLETED,
        events.CLI_UNINSTALLED,
    ]
    assert not reporting.exists()
    assert not list(reporting.parent.glob("events.jsonl.*.sending"))


def test_the_user_agent_is_set_because_the_default_one_is_blocked(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The CDN in front of the ingest host 403s ``Python-urllib/*`` (error 1010).

    urllib supplies that header itself when the caller does not, so an omission
    here is not a missing nicety — it is every event silently discarded.
    """
    events.record(events.CLI_INSTALL_COMPLETED, host="codex")
    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)
    events.flush()

    agent = {key.title(): value for key, value in posted.headers[0].items()}["User-Agent"]
    assert agent.startswith("memu-cli/")
    assert "urllib" not in agent


def test_the_api_key_rides_along_when_present_and_is_absent_otherwise(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events.record(events.CLI_INSTALL_COMPLETED, host="codex")
    anonymous = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", anonymous)
    events.flush()
    # Local-mode users have no key at all and must stay first-class.
    assert "Authorization" not in {key.title(): value for key, value in anonymous.headers[0].items()}

    events.record(events.CLI_INSTALL_COMPLETED, host="codex")
    identified = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", identified)
    monkeypatch.setenv("MEMU_CLOUD_API_KEY", "sk-live-abc")
    events.flush()
    assert {key.title(): value for key, value in identified.headers[0].items()}["Authorization"] == "Bearer sk-live-abc"


@pytest.mark.parametrize("status", [500, 503, 429])
def test_a_transient_failure_retains_the_events(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    events.record(events.CLI_INSTALL_COMPLETED, host="codex")
    error = urllib.error.HTTPError("https://example.invalid/events", status, "nope", {}, None)  # type: ignore[arg-type]
    monkeypatch.setattr(events.urllib.request, "urlopen", _Posted(error=error))

    assert events.flush() == (0, 0)
    assert list(reporting.parent.glob("events.jsonl.*.sending"))


@pytest.mark.parametrize("status", [400, 422])
def test_a_permanent_rejection_is_discarded_rather_than_wedging_the_spool(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    events.record(events.CLI_INSTALL_COMPLETED, host="codex")
    error = urllib.error.HTTPError("https://example.invalid/events", status, "nope", {}, None)  # type: ignore[arg-type]
    monkeypatch.setattr(events.urllib.request, "urlopen", _Posted(error=error))

    # Rejected is counted apart from accepted: a backend rejecting everything
    # must never read as healthy delivery.
    assert events.flush() == (0, 1)
    assert not list(reporting.parent.glob("events.jsonl.*.sending"))


def test_a_retained_file_is_picked_up_by_the_next_flush(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events.record(events.CLI_INSTALL_COMPLETED, host="codex")
    monkeypatch.setattr(events.urllib.request, "urlopen", _Posted(error=OSError("offline")))
    events.flush()

    monkeypatch.setattr(events.urllib.request, "urlopen", _Posted())
    assert events.flush() == (1, 0)


def test_a_truncated_line_costs_one_event_not_the_file(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events.record(events.CLI_INSTALL_COMPLETED, host="codex")
    events.record(events.CLI_UNINSTALLED, host="codex")
    # The signature of a process killed mid-append: a partial *final* line.
    with open(reporting, "a", encoding="utf-8") as handle:
        handle.write('{"event_name": "clie')

    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)
    assert events.flush() == (2, 0)


def test_the_spool_is_capped_and_the_loss_is_reported_not_silent(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(events, "MAX_SPOOL_BYTES", 1)
    events.record(events.CLI_INSTALL_COMPLETED, host="codex")  # lands: cap checked before writing
    events.record(events.CLI_INSTALL_COMPLETED, host="codex")  # dropped
    events.record(events.CLI_INSTALL_COMPLETED, host="codex")  # dropped
    assert len(_spooled(reporting)) == 1

    monkeypatch.setattr(events, "MAX_SPOOL_BYTES", 1024 * 1024)
    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)
    events.flush()
    names = [event["event_name"] for event in posted.events]
    assert events.CLI_EVENTS_DROPPED in names
    dropped = next(e for e in posted.events if e["event_name"] == events.CLI_EVENTS_DROPPED)
    assert dropped["properties"]["dropped_count"] == 2


def test_a_flush_is_bounded_and_the_next_one_resumes_where_it_stopped(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The budget must not cost events, and must not stall on the same ones.

    One POST per event means a long backlog is a long stream of requests, so a
    flush stops at :data:`MAX_FLUSH_POSTS`. The undelivered tail is written back,
    which is what stops the next flush from spending its budget re-posting the
    same leading events forever — a cap without that is a spool that never drains.
    """
    monkeypatch.setattr(events, "MAX_FLUSH_POSTS", 3)
    for _ in range(7):
        events.record(events.CLI_INSTALL_COMPLETED, host="codex")
    spooled = [event["event_id"] for event in _spooled(reporting)]

    delivered: list[str] = []
    for expected in (3, 3, 1):
        posted = _Posted()
        monkeypatch.setattr(events.urllib.request, "urlopen", posted)
        assert events.flush() == (expected, 0)
        delivered += [event["event_id"] for event in posted.events]

    # Every event exactly once, in order, and nothing left behind.
    assert delivered == spooled
    assert not list(reporting.parent.glob("events.jsonl.*"))


def test_send_now_has_no_caller_in_the_shipped_code() -> None:
    # It exists so the transport seam is proven to admit both modes, and is
    # deliberately dormant (ADR 0016 section 2). If this fails, someone wired it
    # up — which is a decision that owes a reason, not an accident.
    root = pathlib.Path(events.__file__).parent
    callers = [
        path
        for path in root.rglob("*.py")
        if path.name != "events.py" and "send_now(" in path.read_text(encoding="utf-8")
    ]
    assert callers == []


# --------------------------------------------------------------------------- #
# The CLI surface
# --------------------------------------------------------------------------- #


def test_report_verbs_exist_on_every_host(reporting: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    for spec in (CODEX_SPEC, CLAUDE_SPEC):
        assert run(spec, ["report", "install"]) == 0
    assert len(_spooled(reporting)) == 2
    assert {event["agent_platform"] for event in _spooled(reporting)} == {"codex", "claude_code"}


def test_the_install_funnel_has_a_code_observed_start_and_a_reported_end(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Printing the guide *is* the start signal, and it delivers on the spot.

    ``report install`` is prose-driven and undercounts by design. If the start
    were too, the funnel could report more completions than attempts — so the
    start is taken where code can see it, and only the completion needs a verb.
    """
    monkeypatch.setenv("MEMU_DOCS_BASE_URL", "")
    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    assert run(CLAUDE_SPEC, ["docs", "install"]) == 0
    assert capsys.readouterr().out.strip(), "the guide itself must still be what this command prints"
    assert run(CLAUDE_SPEC, ["report", "install"]) == 0

    assert [event["event_name"] for event in posted.events] == [events.CLI_INSTALL_STARTED]
    # The completion keeps the ordinary treatment: spooled, carried by a bridging run.
    assert [event["event_name"] for event in _spooled(reporting)] == [events.CLI_INSTALL_COMPLETED]
    assert all(event["properties"] == {} for event in _spooled(reporting) + posted.events)


def test_the_install_start_carries_the_backlog_off_a_machine_that_may_never_bridge(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Why ``docs install`` flushes rather than only recording.

    An install that dies in Part 2 never reaches ``prepare`` or ``commit``, so
    this is the only flush point its earlier events will ever see — and those are
    exactly the events that explain why it died.
    """
    monkeypatch.setenv("MEMU_DOCS_BASE_URL", "")
    events.record_cli_error(RuntimeError("an earlier doctor"), command="doctor", host="claude-code")
    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    assert run(CLAUDE_SPEC, ["docs", "install"]) == 0

    assert [event["event_name"] for event in posted.events] == [
        events.CLI_ERROR,
        events.CLI_INSTALL_STARTED,
    ]
    assert not reporting.exists()


def test_only_the_install_guide_reports_an_attempt(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # `docs task` runs on every scheduled-task repair and `docs uninstall` is the
    # opposite intent; neither is an install attempt.
    monkeypatch.setenv("MEMU_DOCS_BASE_URL", "")
    assert run(CLAUDE_SPEC, ["docs", "task"]) == 0
    assert run(CLAUDE_SPEC, ["docs", "uninstall"]) == 0
    assert _spooled(reporting) == []


def test_report_install_and_uninstall_take_no_failure_flag(reporting: pathlib.Path) -> None:
    # Success-only by decision: failure has exactly one channel, `report error`.
    with pytest.raises(SystemExit):
        run(CODEX_SPEC, ["report", "install", "--failed"])


def test_report_error_rejects_a_stage_outside_the_vocabulary(reporting: pathlib.Path) -> None:
    with pytest.raises(SystemExit):
        run(CODEX_SPEC, ["report", "error", "--stage", "whatever"])


def test_report_error_records_stage_and_detail(reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    assert run(CODEX_SPEC, ["report", "error", "--stage", "install", "--detail", "pip resolved no wheel"]) == 0

    # Delivered inline, not left for a later flush: the runs that file an error are
    # disproportionately the runs that never reach `prepare` or `commit`.
    (event,) = posted.events
    assert not reporting.exists()
    assert event["event_name"] == events.CORE_ACTION_FAILED
    # `action_name` mirrors `stage` at the envelope, so the failure event carries
    # the same discriminator `core_action_completed` does. The CLI surface stays
    # `--stage` only — nothing asks an agent for a second name for one thing.
    assert event["properties"] == {
        "stage": "install",
        "action_name": "install",
        "detail": "pip resolved no wheel",
    }


def test_report_uninstall_delivers_immediately(reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # It cannot wait for a later flush: `UNINSTALL.md` Part 3 may remove the very
    # binary that would deliver it.
    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    assert run(CODEX_SPEC, ["report", "uninstall"]) == 0
    assert [event["event_name"] for event in posted.events] == [events.CLI_UNINSTALLED]
    assert not reporting.exists()


def test_report_says_so_when_reporting_is_switched_off(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MEMU_TELEMETRY", "0")
    assert run(CODEX_SPEC, ["report", "install"]) == 0
    assert "nothing recorded" in capsys.readouterr().out


def test_retrieve_records_counts_and_never_the_query(reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from memu.hosts import retrieval

    async def _fake(query: str, where: Any = None) -> dict[str, Any]:
        return {"segments": [{"text": "a"}, {"text": "b"}], "files": [{"name": "f"}], "resources": []}

    monkeypatch.setattr(retrieval, "retrieve", _fake)
    assert run(CODEX_SPEC, ["retrieve", "my bank password reminder"]) == 0

    (event,) = _spooled(reporting)
    assert event["event_name"] == events.CORE_ACTION_COMPLETED
    assert event["properties"]["action_name"] == "memory_search"
    assert event["properties"]["success"] is True
    assert event["properties"]["result_count"] == 3
    assert "bank password" not in json.dumps(event)


def test_a_failing_retrieve_never_posts_from_the_per_turn_hook(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The invariant that survives the error path too.

    A store the hook cannot reach fails ``retrieve`` on *every* turn. If the error
    handler flushed, that would put a blocking POST on the hot path once per turn,
    precisely when the user is already broken.
    """
    from memu.hosts import retrieval

    async def _boom(query: str, where: Any = None) -> dict[str, Any]:
        raise RuntimeError("boom")

    posted = _Posted()
    monkeypatch.setattr(retrieval, "retrieve", _boom)
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    assert run(CODEX_SPEC, ["retrieve", "anything"]) == 1
    assert posted.events == []
    # Recorded, just not delivered from here — the bridging pair will carry it.
    assert len(_spooled(reporting)) == 2


def test_a_failing_bridging_run_does_flush_because_its_flush_point_is_what_broke(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from memu.hosts import host_cli

    async def _boom(layout: Any) -> dict[str, Any]:
        raise RuntimeError("boom")

    posted = _Posted()
    monkeypatch.setattr(host_cli, "commit", _boom)
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    assert run(CODEX_SPEC, ["commit"]) == 1
    names = [event["event_name"] for event in posted.events]
    assert events.CLI_ERROR in names


def test_a_failing_command_records_both_the_action_and_the_exception(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from memu.hosts import retrieval

    async def _boom(query: str, where: Any = None) -> dict[str, Any]:
        raise RuntimeError("boom")

    monkeypatch.setattr(retrieval, "retrieve", _boom)
    monkeypatch.setattr(events.urllib.request, "urlopen", _Posted(error=OSError("offline")))

    assert run(CODEX_SPEC, ["retrieve", "anything"]) == 1
    # The spool was rotated by the error handler's flush, which then failed.
    spooled = [
        json.loads(line)
        for path in reporting.parent.glob("events.jsonl*")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    names = [event["event_name"] for event in spooled]
    assert events.CORE_ACTION_COMPLETED in names
    assert events.CLI_ERROR in names
    action = next(e for e in spooled if e["event_name"] == events.CORE_ACTION_COMPLETED)
    assert action["properties"]["success"] is False


# --------------------------------------------------------------------------- #
# The agent-facing text
# --------------------------------------------------------------------------- #

_GUIDES = sorted((pathlib.Path(events.__file__).parent / "hosts").glob("*/*.md"))


def _guides_naming(verb: str) -> list[pathlib.Path]:
    return [path for path in _GUIDES if verb in path.read_text(encoding="utf-8")]


def _flat(path: pathlib.Path) -> str:
    """The guide as one line, so a phrase split across a wrap still matches."""
    return " ".join(path.read_text(encoding="utf-8").split())


@pytest.mark.parametrize("guide", _guides_naming("report error"), ids=lambda path: f"{path.parent.name}/{path.name}")
def test_no_guide_asks_for_report_error_without_the_scrubbing_sentence(guide: pathlib.Path) -> None:
    """ADR 0016 section 5's gate, as a test rather than a promise.

    ``--detail`` is the highest-leakage surface in the feature: an LLM chooses the
    payload and its context is the user's transcript. The byte cap is enforced in
    code and cannot be forgotten; *what* goes in is guided prompt-side only, so
    the instruction may never ship without the sentence that scopes it. A guide
    that gains the verb and forgets the scrubbing is exactly what this locks out.

    ``command output`` is the discriminating phrase — the other two occur in
    ordinary guide prose as well.
    """
    text = _flat(guide)
    for phrase in ("credential", "absolute path", "command output"):
        assert phrase in text, f"asks for `report error` without ruling out {phrase!r}"


@pytest.mark.parametrize(
    "guide", _guides_naming("report uninstall"), ids=lambda path: f"{path.parent.name}/{path.name}"
)
def test_uninstall_is_reported_before_the_package_can_be_removed(guide: pathlib.Path) -> None:
    """Placement is what makes this event reliable, not any retry.

    ``report uninstall`` delivers inline precisely because the package removal
    below it may take away the binary that would otherwise have flushed it later.
    A guide that lets the two swap order silently loses every uninstall on the
    last host of a machine — the one case the event exists to see.
    """
    text = _flat(guide)
    removals = [text.index(marker) for marker in ("pip uninstall", "Remove `memu-cli`") if marker in text]
    assert removals, "uninstall guide no longer says how the package goes"
    assert text.index("report uninstall") < min(removals)
