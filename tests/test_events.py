"""Client event reporting (ADR 0016).

Weighted toward the two properties that matter more than delivery: **nothing
leaks**, and **nothing breaks**. A telemetry module that loses events is a
disappointment; one that ships a user's memory content, or that turns a working
``retrieve`` into a failed one, is a defect of a different kind.
"""

from __future__ import annotations

import json
import pathlib
import time
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

_CONTEXT_FIELDS = frozenset({"client_version", "agent_platform", "os", "deployment_mode", "session_id"})
"""Everything the ingest schema wants under ``context``. Asserted absent from the
top level as well as present below it: sending one of these top-level is a
permanent 4xx, which the flush discards rather than retries, so a regression here
would lose events silently rather than fail loudly."""


def test_envelope_carries_every_field_the_backend_expects(reporting: pathlib.Path) -> None:
    events.record(events.CLI_INSTALL_SUCCEEDED, host="claude-code")

    (event,) = _spooled(reporting)
    assert set(event) >= {
        "event_id",
        "event_name",
        "client_type",
        "client_instance_id",
        "occurred_at",
        "context",
        "properties",
    }
    assert event["client_type"] == "memu_cli"
    assert event["occurred_at"].endswith("Z")
    # The environment dimensions are nested, not top-level: the ingest schema
    # rejects them at the top level, and a rejection is a permanent 4xx the flush
    # discards rather than retries.
    assert set(event["context"]) == {
        "client_version",
        "agent_platform",
        "os",
        "deployment_mode",
        "reported_by",
    }
    assert event["context"]["deployment_mode"] == "local"
    assert not _CONTEXT_FIELDS & set(event)


def test_reported_by_separates_what_code_saw_from_what_a_model_asserted(reporting: pathlib.Path) -> None:
    # Three name families mix an exact `_started`/`_succeeded` with a voluntary,
    # undercounting `_failed`, so `succeeded + failed` never sums to `started`
    # there. This field is what makes that one predicate away rather than a fact a
    # consumer has to already know.
    events.record(events.MEMORY_UPDATE_STARTED, host="codex")
    events.record(events.MEMORY_UPDATE_FAILED, host="codex")
    started, failed = _spooled(reporting)
    assert started["context"]["reported_by"] == "code"
    assert failed["context"]["reported_by"] == "agent"

    # Derived from the name, never passed in, so a call site cannot get it wrong.
    assert events.reported_by(events.MEMORY_SEARCH_FAILED) == "code"
    assert events.reported_by(events.CLI_INSTALL_SUCCEEDED) == "agent"


def test_event_ids_are_unique_so_a_retry_can_be_deduplicated(reporting: pathlib.Path) -> None:
    events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")
    events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")

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
    events.record(events.CLI_INSTALL_SUCCEEDED, host="claude-code", session_id_env="CLAUDE_CODE_SESSION_ID")
    (absent,) = _spooled(reporting)
    assert "session_id" not in absent["context"]

    reporting.unlink()
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "abc-123")
    events.record(events.CLI_INSTALL_SUCCEEDED, host="claude-code", session_id_env="CLAUDE_CODE_SESSION_ID")
    (present,) = _spooled(reporting)
    assert present["context"]["session_id"] == "abc-123"
    assert "session_id" not in present, "nested like the rest of the context, never top-level"


def test_client_instance_id_persists_in_config_and_survives_a_reinstall(
    reporting: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    from memu import env as env_module

    events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")
    first = _spooled(reporting)[0]["client_instance_id"]

    # `UNINSTALL.md` Part 3 keeps config.env unconditionally, which is the whole
    # reason the id lives there: install -> uninstall -> reinstall stays one
    # instance's history.
    assert f"MEMU_CLIENT_ID={first}" in (tmp_path / "config.env").read_text(encoding="utf-8")

    env_module.reload()
    reporting.unlink()
    events.record(events.CLI_UNINSTALL_SUCCEEDED, host="codex")
    assert _spooled(reporting)[0]["client_instance_id"] == first


# --------------------------------------------------------------------------- #
# Nothing leaks
# --------------------------------------------------------------------------- #


def test_properties_are_an_allowlist_not_a_passthrough(reporting: pathlib.Path) -> None:
    events.record(
        events.MEMORY_SEARCH_SUCCEEDED,
        host="codex",
        properties={
            "result_count": 3,
            # Everything below is exactly what must never leave the machine.
            "query": "what did I tell you about my salary",
            "store_dsn": "postgres://user:pw@host/db",
            "path": "/Users/someone/secret-project/notes.md",
        },
    )

    (event,) = _spooled(reporting)
    assert event["properties"] == {"result_count": 3}


def test_one_allowlist_per_action_not_the_union_of_every_action(reporting: pathlib.Path) -> None:
    # The payoff of splitting `core_action_completed` by action: a read event can no
    # longer carry a write's counts, and a write cannot carry a read's, purely
    # because one shared entry had to admit the union of both.
    events.record(
        events.MEMORY_SEARCH_SUCCEEDED,
        host="codex",
        properties={"result_count": 3, "recall_file_count": 9, "session_count": 2},
    )
    events.record(
        events.MEMORY_COMMIT_SUCCEEDED,
        host="codex",
        properties={"recall_file_count": 9, "result_count": 3},
    )
    search, commit = _spooled(reporting)
    assert search["properties"] == {"result_count": 3}
    assert commit["properties"] == {"recall_file_count": 9}


def test_outcome_in_the_name_means_no_outcome_in_the_properties(reporting: pathlib.Path) -> None:
    # A `success` field would now be constant per event name — teaching a consumer
    # nothing while inviting someone to later send the other value, contradicting
    # the name it sits beside.
    events.record(events.CLI_INSTALL_SUCCEEDED, host="codex", properties={"success": True})
    events.record(events.MEMORY_UPDATE_FAILED, host="codex", properties={"success": False, "detail": "nope"})
    assert [event["properties"] for event in _spooled(reporting)] == [{}, {}]


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

    # One dedup decision covers both projections of a report, so a retry loop files
    # neither a duplicate prose row nor a duplicate counter — a gate that let one
    # through would silently make the counter the less trustworthy of the pair.
    assert [event["event_name"] for event in _spooled(reporting)] == [
        events.AGENT_ERROR_REPORTED,
        events.MEMORY_UPDATE_FAILED,
        events.AGENT_ERROR_REPORTED,
    ]


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

    assert [event["event_name"] for event in posted.events] == [
        events.AGENT_ERROR_REPORTED,
        events.CLI_INSTALL_FAILED,
    ]


def test_agent_error_reports_again_once_the_dedup_window_has_passed(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A failure still happening an hour later is a different fact, and worth a row.
    events.record_agent_error(stage="install", detail="no wheel", host="codex")
    monkeypatch.setattr(events, "ERROR_DEDUP_SECONDS", 0.0)
    events.record_agent_error(stage="install", detail="no wheel", host="codex")

    names = [event["event_name"] for event in _spooled(reporting)]
    assert names.count(events.AGENT_ERROR_REPORTED) == 2
    assert names.count(events.CLI_INSTALL_FAILED) == 2


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
    events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")
    events.record_agent_error(stage="other", detail="nope", host="codex")

    assert not reporting.exists()
    assert events.flush() == (0, 0)


def test_recording_survives_an_unwritable_spool(reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMU_EVENTS_SPOOL", "/definitely/not/a/writable/path/events.jsonl")
    events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")  # must not raise


def test_recording_survives_broken_config(reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # `memory_mode()` raises on this. Reporting must not be what surfaces it.
    monkeypatch.setenv("MEMU_MEMORY_MODE", "nonsense")
    events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")
    assert not reporting.exists()


def test_flush_survives_an_unreachable_endpoint(reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")
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
    events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")
    events.record(events.CLI_UNINSTALL_SUCCEEDED, host="codex")
    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    assert events.flush() == (2, 0)
    # Two events, two requests, spool order preserved.
    assert [event["event_name"] for event in posted.events] == [
        events.CLI_INSTALL_SUCCEEDED,
        events.CLI_UNINSTALL_SUCCEEDED,
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
    events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")
    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)
    events.flush()

    agent = {key.title(): value for key, value in posted.headers[0].items()}["User-Agent"]
    assert agent.startswith("memu-cli/")
    assert "urllib" not in agent


def test_the_api_key_rides_along_when_present_and_is_absent_otherwise(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")
    anonymous = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", anonymous)
    events.flush()
    # Local-mode users have no key at all and must stay first-class.
    assert "Authorization" not in {key.title(): value for key, value in anonymous.headers[0].items()}

    events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")
    identified = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", identified)
    monkeypatch.setenv("MEMU_CLOUD_API_KEY", "sk-live-abc")
    events.flush()
    assert {key.title(): value for key, value in identified.headers[0].items()}["Authorization"] == "Bearer sk-live-abc"


@pytest.mark.parametrize("status", [500, 503, 429])
def test_a_transient_failure_retains_the_events(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")
    error = urllib.error.HTTPError("https://example.invalid/events", status, "nope", {}, None)  # type: ignore[arg-type]
    monkeypatch.setattr(events.urllib.request, "urlopen", _Posted(error=error))

    assert events.flush() == (0, 0)
    assert list(reporting.parent.glob("events.jsonl.*.sending"))


@pytest.mark.parametrize("status", [400, 422])
def test_a_permanent_rejection_is_discarded_rather_than_wedging_the_spool(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")
    error = urllib.error.HTTPError("https://example.invalid/events", status, "nope", {}, None)  # type: ignore[arg-type]
    monkeypatch.setattr(events.urllib.request, "urlopen", _Posted(error=error))

    # Rejected is counted apart from accepted: a backend rejecting everything
    # must never read as healthy delivery.
    assert events.flush() == (0, 1)
    assert not list(reporting.parent.glob("events.jsonl.*.sending"))


def test_a_retained_file_is_picked_up_by_the_next_flush(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")
    monkeypatch.setattr(events.urllib.request, "urlopen", _Posted(error=OSError("offline")))
    events.flush()

    monkeypatch.setattr(events.urllib.request, "urlopen", _Posted())
    assert events.flush() == (1, 0)


def test_a_truncated_line_costs_one_event_not_the_file(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")
    events.record(events.CLI_UNINSTALL_SUCCEEDED, host="codex")
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
    events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")  # lands: cap checked before writing
    events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")  # dropped
    events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")  # dropped
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
        events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")
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


def test_only_retrieve_delivers_inline(reporting: pathlib.Path) -> None:
    """``deliver=True`` is the per-turn hook's alone (ADR 0016 section 2).

    It puts a blocking POST on the calling command, which is affordable exactly
    once, on the one path whose event the backend wants promptly. If this fails
    someone wired it to a second call site — a decision that owes a reason, not an
    accident.
    """
    root = pathlib.Path(events.__file__).parent
    callers = sorted(
        path.name
        for path in root.rglob("*.py")
        if path.name != "events.py"
        # Comment lines are skipped so that *explaining* this path — which several
        # docstrings around the codebase now do — cannot trip a tripwire meant for
        # a second caller.
        and any(
            "deliver=True" in line and not line.lstrip().startswith("#")
            for line in path.read_text(encoding="utf-8").splitlines()
        )
    )
    assert callers == ["retrieval.py"]


def test_delivering_an_event_posts_it_alone_and_never_drains_the_spool(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bound that lets the per-turn hook report at all.

    A flush would send everything spooled, one POST each. This sends one, however
    far behind the machine has fallen — so the hook's cost is a constant, not a
    function of the backlog.
    """
    for _ in range(5):
        events.record(events.CLI_INSTALL_SUCCEEDED, host="codex")
    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    events.record(events.MEMORY_SEARCH_SUCCEEDED, host="codex", properties={"result_count": 1}, deliver=True)

    assert [event["event_name"] for event in posted.events] == [events.MEMORY_SEARCH_SUCCEEDED]
    # The backlog is untouched — not read, not rewritten, not sent — and the
    # delivered event was never appended to it.
    assert [event["event_name"] for event in _spooled(reporting)] == [events.CLI_INSTALL_SUCCEEDED] * 5


def test_an_undelivered_event_falls_back_to_the_spool(reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Inline delivery must not become fire-and-forget.

    An offline laptop is exactly where these events matter, so a POST that does not
    land leaves the event spooled for the bridging pair — the same bargain every
    other path makes, and the reason this is not a bare send.
    """
    monkeypatch.setattr(events.urllib.request, "urlopen", _Posted(error=OSError("no route to host")))

    events.record(events.MEMORY_SEARCH_SUCCEEDED, host="codex", properties={"result_count": 1}, deliver=True)

    (event,) = _spooled(reporting)
    assert event["event_name"] == events.MEMORY_SEARCH_SUCCEEDED


def test_a_permanently_rejected_event_is_not_spooled_to_be_rejected_again(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A 4xx means the server will refuse this payload every time, so holding it
    # only buys a second refusal on the next flush — the same call `_flush` makes.
    error = urllib.error.HTTPError("https://example.invalid/events", 422, "Unprocessable", {}, None)  # type: ignore[arg-type]
    monkeypatch.setattr(events.urllib.request, "urlopen", _Posted(error=error))

    events.record(events.MEMORY_SEARCH_SUCCEEDED, host="codex", properties={"result_count": 1}, deliver=True)

    assert _spooled(reporting) == []


# --------------------------------------------------------------------------- #
# The CLI surface
# --------------------------------------------------------------------------- #


def test_report_verbs_exist_on_every_host(reporting: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    for spec in (CODEX_SPEC, CLAUDE_SPEC):
        assert run(spec, ["report", "install"]) == 0
    assert len(_spooled(reporting)) == 2
    assert {event["context"]["agent_platform"] for event in _spooled(reporting)} == {"codex", "claude_code"}


def test_the_install_funnel_has_a_code_observed_start_and_a_reported_end(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The two steps in are code-observed; only the completion needs a verb.

    ``init`` is ``SKILL.md`` Step 2 and starts the funnel; printing the guide is
    Step 3 and is its own, narrower row. ``report install`` is prose-driven and
    undercounts by design — if a start did too, the funnel could report more
    completions than attempts, so neither step is asked for in prose.
    """
    monkeypatch.setenv("MEMU_DOCS_BASE_URL", "")
    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    assert run(CLAUDE_SPEC, ["init"]) == 0
    assert run(CLAUDE_SPEC, ["docs", "install"]) == 0
    assert capsys.readouterr().out.strip(), "the guide itself must still be what this command prints"
    assert run(CLAUDE_SPEC, ["report", "install"]) == 0

    assert [event["event_name"] for event in posted.events] == [
        events.CLI_INSTALL_STARTED,
        events.INSTALL_GUIDE_OPENED,
    ]
    # The completion keeps the ordinary treatment: spooled, carried by a bridging run.
    assert [event["event_name"] for event in _spooled(reporting)] == [events.CLI_INSTALL_SUCCEEDED]
    assert all(event["properties"] == {} for event in _spooled(reporting) + posted.events)


def test_the_install_start_reports_the_client_id_init_just_wrote(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Why the start is emitted *after* the write, not beside the client id.

    ``init`` mints ``MEMU_CLIENT_ID`` into ``config.env``, and an envelope built
    before that lands would find none in the environment and persist a second one
    — leaving the machine's first event reporting under an id its own config file
    does not contain.
    """
    from memu import config_file

    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    assert run(CLAUDE_SPEC, ["init"]) == 0

    stored = config_file.read()["MEMU_CLIENT_ID"]
    assert [event["client_instance_id"] for event in posted.events] == [stored]
    assert stored[:4] in capsys.readouterr().out, "and it is the id the `client` row named"


def test_the_install_start_is_attributed_when_init_was_given_a_key(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The ordering ADR 0017 was written for: the first event carries the account.

    ``docs install`` fired the start before any key existed, so a first install
    reported anonymously. ``init`` holds the key and writes it before reporting.
    """
    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    assert run(CLAUDE_SPEC, ["init", "--cloud-api-key", "sk-live-abc"]) == 0

    sent = {key.title(): value for key, value in posted.headers[0].items()}
    assert sent["Authorization"] == "Bearer sk-live-abc"


def test_the_install_start_carries_the_backlog_off_a_machine_that_may_never_bridge(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Why ``init`` flushes rather than only recording.

    An install that dies before the bridging pair ever runs never reaches
    ``prepare`` or ``commit``, so this is the only flush point its earlier events
    will ever see — and those are exactly the events that explain why it died.
    """
    events.record_cli_error(RuntimeError("an earlier doctor"), command="doctor", host="claude-code")
    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    assert run(CLAUDE_SPEC, ["init"]) == 0

    assert [event["event_name"] for event in posted.events] == [
        events.CLI_ERROR,
        events.CLI_INSTALL_STARTED,
    ]
    assert not reporting.exists()


def test_only_the_install_guide_reports_being_opened(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # `docs task` runs on every scheduled-task repair and `docs uninstall` is the
    # opposite intent; neither is a step on the way in.
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
    assert not reporting.exists()
    # One report projected twice: the prose for a human, the counter for the funnel.
    report, concrete = posted.events
    assert report["event_name"] == events.AGENT_ERROR_REPORTED
    assert report["properties"] == {"stage": "install", "detail": "pip resolved no wheel"}
    # No `action_name` any more — it asserted a join to `core_action_completed` that
    # never worked, and under the split it would sit beside a real
    # `memory_update_failed`. The CLI surface stays `--stage` only.
    assert "action_name" not in report["properties"]
    # The counter carries nothing: `--detail` has exactly one destination on the
    # wire, so there is exactly one place to audit and truncate it.
    assert concrete["event_name"] == events.CLI_INSTALL_FAILED
    assert concrete["properties"] == {}
    assert concrete["context"]["reported_by"] == "agent"


@pytest.mark.parametrize(
    ("stage", "concrete"),
    [
        ("install", events.CLI_INSTALL_FAILED),
        ("uninstall", events.CLI_UNINSTALL_FAILED),
        ("remember", events.MEMORY_UPDATE_FAILED),
    ],
)
def test_taught_stages_also_emit_a_concrete_failure_event(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, stage: str, concrete: str
) -> None:
    # Exactly the three stages an agent is actually directed to: `INSTALL.md`,
    # `UNINSTALL.md`, and `BRIDGING_TASK.md` each name one.
    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    assert run(CODEX_SPEC, ["report", "error", "--stage", stage, "--detail", "d"]) == 0
    assert [event["event_name"] for event in posted.events] == [events.AGENT_ERROR_REPORTED, concrete]


@pytest.mark.parametrize("stage", ["retrieve", "other"])
def test_unreachable_stages_report_prose_only(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    # No instruction points an agent at either, so a concrete event would be a name
    # that is almost always zero. For `retrieve` it would be worse: a code-observed
    # `memory_search_failed` means "the command raised", while an agent reporting
    # that stage means "retrieval has silently returned nothing for a week" — the
    # rare signal this whole feature exists for, buried inside the common one.
    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    assert run(CODEX_SPEC, ["report", "error", "--stage", stage, "--detail", "d"]) == 0
    assert [event["event_name"] for event in posted.events] == [events.AGENT_ERROR_REPORTED]
    assert events.MEMORY_SEARCH_FAILED not in events.STAGE_FAILURE_EVENTS.values()


def test_report_uninstall_delivers_immediately(reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # It cannot wait for a later flush: `UNINSTALL.md` Part 3 may remove the very
    # binary that would deliver it.
    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    assert run(CODEX_SPEC, ["report", "uninstall"]) == 0
    assert [event["event_name"] for event in posted.events] == [events.CLI_UNINSTALL_SUCCEEDED]
    assert not reporting.exists()


def test_report_says_so_when_reporting_is_switched_off(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MEMU_TELEMETRY", "0")
    assert run(CODEX_SPEC, ["report", "install"]) == 0
    assert "nothing recorded" in capsys.readouterr().out


def test_retrieve_delivers_counts_and_never_the_query(reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from memu.hosts import retrieval

    async def _fake(query: str, where: Any = None) -> dict[str, Any]:
        return {"segments": [{"text": "a"}, {"text": "b"}], "files": [{"name": "f"}], "resources": []}

    posted = _Posted()
    monkeypatch.setattr(retrieval, "retrieve", _fake)
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)
    assert run(CODEX_SPEC, ["retrieve", "my bank password reminder"]) == 0

    # Delivered on the spot, not left for the bridging pair: the backend asked for
    # this event promptly and accepted the round trip.
    (event,) = posted.events
    assert event["event_name"] == events.MEMORY_SEARCH_SUCCEEDED
    assert event["properties"]["result_count"] == 3
    # Both fields the allowlist admits for a read, so a `latency_ms` dropped from
    # `_READ_COUNTS` is caught here rather than going silently missing.
    assert event["properties"]["latency_ms"] >= 0
    assert "bank password" not in json.dumps(event)
    assert _spooled(reporting) == [], "a delivered event is not also spooled"


def test_a_retrieve_that_cannot_deliver_still_succeeds_and_keeps_its_event(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reporting on the hot path must cost the wait, never the command.

    The result is already on stdout before the POST is attempted, so an endpoint
    that is merely unreachable cannot touch what the agent gets back.
    """
    from memu.hosts import retrieval

    async def _fake(query: str, where: Any = None) -> dict[str, Any]:
        return {"segments": [{"text": "a"}], "files": [], "resources": []}

    monkeypatch.setattr(retrieval, "retrieve", _fake)
    monkeypatch.setattr(events.urllib.request, "urlopen", _Posted(error=OSError("no route to host")))

    assert run(CODEX_SPEC, ["retrieve", "anything"]) == 0
    (event,) = _spooled(reporting)
    assert event["event_name"] == events.MEMORY_SEARCH_SUCCEEDED


def test_a_failing_retrieve_never_posts_from_the_per_turn_hook(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The error path stays spool-only, even though the success path delivers.

    A store the hook cannot reach fails ``retrieve`` on *every* turn. Delivering
    here — or flushing from the CLI's error handler — would put a blocking POST on
    the hot path once per turn, precisely when the user is already broken.
    """
    from memu.hosts import retrieval

    async def _boom(query: str, where: Any = None) -> dict[str, Any]:
        raise RuntimeError("boom")

    posted = _Posted()
    monkeypatch.setattr(retrieval, "retrieve", _boom)
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    assert run(CODEX_SPEC, ["retrieve", "anything"]) == 1
    assert posted.events == []
    # Recorded, just not delivered from here — the next successful retrieve carries
    # these out ahead of its own event, as does the bridging pair.
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
    # The outcome is in the name now, so the failed leg is its own event — and it
    # is code-observed, an exception this command actually raised, never the silent
    # -nothing failure an agent reports through `--stage retrieve`.
    assert events.MEMORY_SEARCH_FAILED in names
    assert events.MEMORY_SEARCH_SUCCEEDED not in names
    assert events.CLI_ERROR in names
    action = next(e for e in spooled if e["event_name"] == events.MEMORY_SEARCH_FAILED)
    assert action["context"]["reported_by"] == "code"


# --------------------------------------------------------------------------- #
# The two clocks, now two events (ADR 0016 §4, §10)
#
# `latency_ms` on `memory_commit_*` is memU's own work inside one process;
# `duration_ms` on `memory_update_succeeded` is the whole prepare -> commit cycle
# across two. The tests below pin the second one's edges, because that is the one
# that can be wrong: it is wall clock by necessity, and a fail-open path must drop
# what it cannot believe rather than invent a number. They also pin the gate that
# decides whether the cycle event exists at all, which is a different question off
# the same marker.
# --------------------------------------------------------------------------- #


def _commit(base: pathlib.Path, monkeypatch: pytest.MonkeyPatch, recall_files: int = 1) -> _Posted:
    """Run the ``commit`` CLI against *base* with the store stubbed out."""
    from memu.hosts import host_cli

    async def _committed(layout: Any) -> dict[str, Any]:
        return {"recall_files": [{"name": str(i)} for i in range(recall_files)], "resources": []}

    posted = _Posted()
    monkeypatch.setattr(host_cli, "commit", _committed)
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)
    assert run(CODEX_SPEC, ["commit", "--base-dir", str(base)]) == 0
    return posted


def _named(posted: _Posted, event_name: str) -> dict[str, Any]:
    event = next(e for e in posted.events if e["event_name"] == event_name)
    properties: dict[str, Any] = event["properties"]
    return properties


def _cycle(posted: _Posted) -> dict[str, Any]:
    return _named(posted, events.MEMORY_UPDATE_SUCCEEDED)


def test_commit_reports_both_clocks_and_clears_the_marker(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """The whole seam: prepare stamps, commit closes the cycle and tidies up."""
    from memu.hosts import host_cli
    from memu.hosts.bridging import Layout

    base = tmp_path / "work"
    layout = Layout.default(host="codex", base=base)
    host_cli._mark_cycle_start(CODEX_SPEC, layout)
    assert layout.run_marker.is_file()

    posted = _commit(base, monkeypatch)
    # Two spans, two events: the store call, and the cycle around it. `latency_ms`
    # is memU's own blocking work in one process; `duration_ms` is prepare ->
    # commit across two, and is mostly the agent's.
    assert _named(posted, events.MEMORY_COMMIT_SUCCEEDED)["latency_ms"] >= 0
    assert "duration_ms" not in _named(posted, events.MEMORY_COMMIT_SUCCEEDED)
    assert _cycle(posted)["duration_ms"] >= 0
    assert "latency_ms" not in _cycle(posted)
    # Reported, so the marker's job is done — otherwise the next cycle would
    # measure from this one's prepare.
    assert not layout.run_marker.exists()


def test_prepare_announces_a_cycle_only_when_the_marker_landed(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """No `_started` this machine cannot later close.

    The marker is what lets `commit` emit the matching `_succeeded`, so announcing a
    cycle without one would manufacture a failure out of a full disk.
    """
    from memu.hosts import host_cli
    from memu.hosts.bridging import Layout

    layout = Layout.default(host="codex", base=tmp_path / "work")
    host_cli._mark_cycle_start(CODEX_SPEC, layout)
    assert [e["event_name"] for e in _spooled(reporting)] == [events.MEMORY_UPDATE_STARTED]

    reporting.unlink()
    # A base whose parent is a file, so the marker's `mkdir` raises — the storage
    # failure the pairing has to survive.
    blocked = tmp_path / "blocked"
    blocked.write_text("not a directory", encoding="utf-8")
    host_cli._mark_cycle_start(CODEX_SPEC, Layout.default(host="codex", base=blocked / "work"))
    assert not reporting.exists()


def test_a_leftover_commit_reports_the_call_but_not_a_cycle(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """`BRIDGING_TASK.md`'s LEFTOVERS step, which commits with no prepare of its own.

    Without the gate one bridging run emits one `_started` and two `_succeeded` —
    leftovers, then step 4 — and `started >= succeeded` stops holding on exactly the
    runs that are already in trouble. The counts are still reported, on the commit
    event, which is the only place a leftover's output is ever visible.
    """
    base = tmp_path / "work"
    posted = _commit(base, monkeypatch, recall_files=3)

    names = [event["event_name"] for event in posted.events]
    assert events.MEMORY_COMMIT_SUCCEEDED in names
    assert events.MEMORY_UPDATE_SUCCEEDED not in names
    assert _named(posted, events.MEMORY_COMMIT_SUCCEEDED)["recall_file_count"] == 3


def test_a_failed_commit_reports_the_call_and_leaves_the_cycle_to_the_agent(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """A failed commit keeps the marker for the retry, so the cycle is not over.

    `memory_update_failed` is agent-reported, because a cycle can also die where no
    code is watching at all — the agent never reached `commit`.
    """
    from memu.hosts import host_cli
    from memu.hosts.bridging import Layout

    base = tmp_path / "work"
    layout = Layout.default(host="codex", base=base)
    host_cli._mark_cycle_start(CODEX_SPEC, layout)

    async def _fails(layout: Any) -> dict[str, Any]:
        raise RuntimeError("boom")

    posted = _Posted()
    monkeypatch.setattr(host_cli, "commit", _fails)
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)
    # Delivered by the CLI's top-level error handler, which flushes.
    assert run(CODEX_SPEC, ["commit", "--base-dir", str(base)]) == 1

    names = [event["event_name"] for event in posted.events]
    assert events.MEMORY_COMMIT_FAILED in names
    assert events.MEMORY_UPDATE_SUCCEEDED not in names
    assert events.MEMORY_UPDATE_FAILED not in names

    # The marker is kept, so the retry closes the cycle the original prepare
    # opened. Clearing it on failure would make every retried cycle unmeasurable.
    assert layout.run_marker.is_file()
    monkeypatch.undo()
    assert _cycle(_commit(base, monkeypatch))["duration_ms"] >= 0


@pytest.mark.parametrize(
    ("started_at", "why"),
    [
        (time.time() + 600, "the clock moved backwards between prepare and commit"),
        (time.time() - 10 * 86400, "the machine slept through a week"),
        ("not-a-number", "the marker is corrupt"),
    ],
)
def test_a_span_that_cannot_be_believed_is_dropped_not_sent(
    reporting: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    started_at: Any,
    why: str,
) -> None:
    from memu.hosts.bridging import Layout

    base = tmp_path / "work"
    layout = Layout.default(host="codex", base=base)
    layout.run_marker.parent.mkdir(parents=True, exist_ok=True)
    layout.run_marker.write_text(json.dumps({"started_at": started_at}), encoding="utf-8")

    # The marker exists, so the cycle happened and still reports — it simply
    # reports no duration. The gate on the event and the gate on this field read
    # the same file and answer two different questions.
    properties = _cycle(_commit(base, monkeypatch))
    assert "duration_ms" not in properties, why


def test_the_cycle_marker_is_host_scoped_like_the_cursor_beside_it(tmp_path: pathlib.Path) -> None:
    """Two hosts bridge independently; one shared marker would cross their cycles."""
    from memu.hosts.bridging import Layout

    codex = Layout.default(host="codex", base=tmp_path)
    claude = Layout.default(host="claude-code", base=tmp_path)
    assert codex.run_marker != claude.run_marker


def test_a_cycle_that_cannot_be_stamped_is_still_a_successful_prepare(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """Reporting is never a dependency — an unwritable marker costs the field only."""
    from memu.hosts import host_cli
    from memu.hosts.bridging import Layout

    def _unwritable(*args: Any, **kwargs: Any) -> None:
        raise OSError("read-only")

    monkeypatch.setattr(pathlib.Path, "write_text", _unwritable)
    host_cli._mark_cycle_start(CODEX_SPEC, Layout.default(host="codex", base=tmp_path))


# --------------------------------------------------------------------------- #
# The store sweep (`memory_list`, ADR 0016 §10)
#
# The one core action with two call sites — `prepare`'s mirror of the store to
# disk, and the core binary's `memu list-files`. What is pinned here is what the
# number means: one event for the whole paginated loop, counting what the store
# returned rather than what the caller kept.
# --------------------------------------------------------------------------- #


class _Store:
    """Serves *pages* one page at a time. With ``boom``, dies after the last one."""

    def __init__(self, pages: list[list[dict[str, Any]]], boom: bool = False) -> None:
        self._pages = pages
        self._boom = boom

    async def list_all_recall_files(
        self, where: Any = None, *, cursor: str | None = None, limit: int = 100
    ) -> dict[str, Any]:
        index = int(cursor or 0)
        if index >= len(self._pages):
            raise RuntimeError("boom")
        more = index + 1 < len(self._pages) or self._boom
        return {"recall_files": self._pages[index], "next_cursor": str(index + 1) if more else None}


def _recall_file(name: str, track: str = "memory") -> dict[str, Any]:
    return {"name": name, "track": track, "description": "d", "content": "c"}


def _sweep(pages: list[list[dict[str, Any]]], boom: bool = False) -> Any:
    """Point the bridging mirror at a fake store."""
    return lambda: _Store(pages, boom=boom)


def _prepare(tmp_path: pathlib.Path) -> list[str]:
    logs = tmp_path / "logs"
    logs.mkdir(exist_ok=True)
    return ["prepare", "--session-dir", str(logs), "--base-dir", str(tmp_path / "work")]


def _listing(events_seen: list[dict[str, Any]], *, success: bool = True) -> dict[str, Any]:
    want = events.MEMORY_LIST_SUCCEEDED if success else events.MEMORY_LIST_FAILED
    (event,) = [e for e in events_seen if e["event_name"] == want]
    properties: dict[str, Any] = event["properties"]
    return properties


def test_prepare_reports_the_whole_sweep_as_one_event_and_delivers_it(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """Two pages and an unmirrorable file: one event, counting all three."""
    from memu.hosts.bridging import pipeline

    pages = [[_recall_file("a"), _recall_file("x", track="nowhere")], [_recall_file("b")]]
    monkeypatch.setattr(pipeline, "build_agentic_memory_backend_from_env", _sweep(pages))
    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    assert run(CLAUDE_SPEC, _prepare(tmp_path)) == 0

    # Delivered, not merely spooled: `prepare` is one of the two flush points.
    properties = _listing(posted.events)
    # Three listed, two mirrored — the unknown track has nowhere to live on disk,
    # but the store still returned it.
    assert properties["result_count"] == 3
    assert properties["latency_ms"] >= 0
    event = next(e for e in posted.events if e["event_name"] == events.MEMORY_LIST_SUCCEEDED)
    assert event["context"]["agent_platform"] == "claude_code", "the pipeline reports the host it ran for"


def test_a_sweep_that_dies_midway_reports_how_far_it_got(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """A partial count, never zero — and the failure still reaches the caller."""
    from memu.hosts.bridging import pipeline

    monkeypatch.setattr(pipeline, "build_agentic_memory_backend_from_env", _sweep([[_recall_file("a")]], boom=True))
    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    assert run(CLAUDE_SPEC, _prepare(tmp_path)) == 1

    properties = _listing(posted.events, success=False)
    assert properties["result_count"] == 1
    # The exception the CLI caught is reported beside it, from its own channel.
    assert events.CLI_ERROR in [e["event_name"] for e in posted.events]


def test_list_files_reports_the_same_action_from_a_binary_with_no_host(
    reporting: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`memu list-files` records and does not flush: a hand-run command must not
    block on a POST, and it is never the last thing to run on a broken machine."""
    from memu import cli

    store = _Store([[_recall_file("a")], [_recall_file("b")]])
    monkeypatch.setattr(cli, "build_agentic_memory_backend_from_env", lambda **kwargs: store)
    posted = _Posted()
    monkeypatch.setattr(events.urllib.request, "urlopen", posted)

    assert cli.main(["list-files"]) == 0

    assert posted.events == [], "nothing on this path flushes"
    properties = _listing(_spooled(reporting))
    assert properties["result_count"] == 2
    (event,) = _spooled(reporting)
    assert event["context"]["agent_platform"] == "none", "the core binary has no host, and says so"
    assert "session_id" not in event["context"]


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
