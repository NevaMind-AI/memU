"""Client event reporting — spool locally, flush on the slow path (ADR 0016).

memU is otherwise blind to its own operation: an install either works or the user
files an issue, and a bridging task that quietly stops producing memory looks
exactly like one that had nothing to mine. This module reports a small, fixed set
of lifecycle events so those two are distinguishable.

Two rules shape everything here, and both are inherited rather than invented:

* **Never a dependency.** :mod:`memu.hosts.templates` already contacts a memU
  server and states the contract — "the server is pure upside". Every function
  below swallows every failure. A ``retrieve`` that cannot record an event is a
  successful ``retrieve``; nothing here may change a command's exit code, its
  output, or its latency in any way a user could notice.
* **The per-turn hook must never fetch.** ``retrieve`` runs on every agent turn,
  and ``_refresh_retrieval`` in :mod:`memu.hosts.host_cli` exists precisely
  because of that. So recording an event *appends one line to a spool* and
  returns; delivery happens later, from the low-frequency bridging pair.

The spool is also what makes ``event_id`` mean anything. Client-generated ids buy
idempotence *for a client that retries* — a fire-and-forget sender never
double-delivers, so it would give the backend nothing to deduplicate. A spool
that survives an offline laptop and re-POSTs on the next flush does. One
decision, not two.

What leaves the machine is counts, never content: no query text, no memory, no
recall-file names, no store DSN, no absolute paths, no transcripts.
:data:`_ALLOWED_PROPERTIES` is where that is enforced, and it is an allowlist so
that adding a leak takes a deliberate edit rather than an oversight.

Switching it off: ``MEMU_TELEMETRY=0`` in ``~/.memu/config.env`` (or the
environment), the conventional ``DO_NOT_TRACK=1``, or an empty
``MEMU_EVENTS_BASE_URL`` — the same escape hatch ``MEMU_TEMPLATE_BASE_URL`` and
``MEMU_DOCS_BASE_URL`` already offer.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import platform
import traceback
import urllib.error
import urllib.request
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from memu.env import CONFIG_ENV, env, env_declared, memory_mode, reload

# --------------------------------------------------------------------------- #
# The wire vocabulary: the endpoint, and every event name the client can emit.
#
# Settled with the backend (ADR 0016 §5). Constants in exactly one place, so a
# later revision stays an edit here and nowhere else.
# --------------------------------------------------------------------------- #

DEFAULT_EVENTS_URL = "https://api.memu.so/api/memu/analytics/events"
"""Override with ``MEMU_EVENTS_BASE_URL``; set it empty to switch reporting off
entirely (air-gapped installs, offline CI, tests)."""

CORE_ACTION_COMPLETED = "core_action_completed"
"""Shared by retrieve and remember; ``properties.action_name`` discriminates."""

CLI_INSTALL_STARTED = "cli_install_started"
"""An install *attempt*, recorded when a host prints its install guide — the
first act on that path which proves ``memu-cli`` is installed and resolving on
``PATH``.

Code-observed rather than agent-reported, and that is the whole point: the
completion below is prose-driven and undercounts (ADR 0016 §4), so a start that
undercounted independently could report more completions than attempts. Two
caveats for whoever reads these. A guide re-printed mid-run — a compaction, a
restarted agent — counts twice, so the denominator is attempts-as-observed, not
distinct machines. And ``deployment_mode`` here predates ``INSTALL.md`` Part 1.2's
backend choice, so it is a default rather than the mode the install lands on:
never join a start to a completion on that field."""

CLI_INSTALL_COMPLETED = "cli_install_completed"
"""The agent reached the guide's final gate. Formerly ``client_installed``."""

CLI_UNINSTALLED = "cli_uninstalled"
"""The agent reached ``UNINSTALL.md``'s final gate — the uninstall counterpart to
:data:`CLI_INSTALL_COMPLETED`, success-only for the same reason. Formerly
``client_uninstalled``."""

CORE_ACTION_FAILED = "core_action_failed"
"""The agent-reported error — model-judged, free-form detail.

Named as the failure counterpart to :data:`CORE_ACTION_COMPLETED`, and carrying
``properties.action_name`` for the same reason: one discriminator field, so a
consumer slices both events the same way. That field mirrors ``--stage``
exactly — see :func:`record_agent_error`, which is where the mirroring happens and
where its one sharp edge is written down. Nothing user-facing gains a name: the
flag, the prose, and every agent-facing instruction still say *stage*."""

CLI_ERROR = "cli_error"
"""The code-observed error, raised from the CLI's top-level handler.

Deliberately *not* the same event as :data:`CORE_ACTION_FAILED`: one is an
exception the CLI actually caught, the other is a model's judgement about the
world. Same word, different provenance, so they must not share a name."""

CLI_EVENTS_DROPPED = "cli_events_dropped"
"""Emitted when the spool hit its cap and events were discarded, so the loss is
reported rather than silent."""

CLIENT_TYPE = "memu_cli"

# --------------------------------------------------------------------------- #
# Bounds. Every one of these exists to stop an unbounded thing.
# --------------------------------------------------------------------------- #

SPOOL_PATH = "~/.memu/events.jsonl"
"""Shared across hosts, because identity is machine-scoped (see
:func:`client_instance_id`) — not under ``~/.memu/hosts/<host>/`` like the rest of
a host's working state. Override with ``MEMU_EVENTS_SPOOL``."""

MAX_SPOOL_BYTES = 1024 * 1024
"""Past this, appends are dropped and counted. The case this exists for is a
machine whose bridging schedule is broken: ``retrieve`` keeps appending every
turn and nothing ever flushes."""

MAX_FLUSH_POSTS = 200
"""Requests one flush may make, so a long offline stretch cannot turn the next
bridging run into an unbounded stream of POSTs.

It bounds *requests* rather than envelopes-per-request because the endpoint takes
one event per POST — see :func:`_post`. Anything still spooled when the budget
runs out stays spooled and goes out on the following flush, so a full spool
drains over several runs instead of stalling one."""

MAX_DETAIL_CHARS = 5000
"""Hard cap on the agent's free-form ``--detail``. Without it an agent can paste a
whole transcript — a privacy dump and an unbounded body at once. Truncation is
one line of code and, unlike a prompt, cannot be forgotten."""

MAX_FRAMES = 20
"""Traceback frames kept on a ``cli_error``, innermost last."""

ERROR_DEDUP_SECONDS = 3600.0
"""How long one ``(stage, detail)`` pair stays deduplicated (:func:`_claim_error`).

A window in wall-clock, not "until the next flush", because ``report error``
flushes inline: the spool it would have been measured against is empty by the time
the agent retries. An hour covers the case the dedup exists for — an agent looping
on the same failure inside one session — while still letting a failure that is
*still* happening tomorrow report itself again, which is a different fact and
worth a row."""

MAX_LEDGER_ENTRIES = 200
"""Fingerprints kept in the dedup ledger. Bounds a file that is otherwise appended
to forever; oldest go first, and losing one only costs a duplicate."""

_TIMEOUT_SECONDS = 5.0

STAGES: tuple[str, ...] = ("install", "uninstall", "remember", "retrieve", "other")
"""The closed vocabulary for an agent-reported error's ``--stage``.

``retrieve`` covers the failure this whole feature exists for: a retrieval that
returns nothing *forever* throws no exception, so :data:`CLI_ERROR` cannot see it
— record and inject have silently disagreed about the store (ADR 0009's opening
argument), and only an agent can notice. ``other`` is the escape hatch: a closed
enum that rejects unknowns converts *unclassifiable* into *unreported*, which is
the exact loss this feature exists to prevent.

Coarse on purpose, and it will be refined. New values must be **hierarchical**
(``install.part2.schedule``, not ``install_schedule_failed``) so a
``stage LIKE 'install%'`` query survives the granularity change — which means
consumers must tolerate unknown values rather than reject them. The check below is
validation at the point of entry, not a promise that the set is final.
"""

# ``--code``, a structured error vocabulary alongside ``--detail``, is reserved
# and deliberately unimplemented (ADR 0016 §5). No good definition of one exists
# yet, and an unvalidated free-text field in the meantime would collect a year of
# ad-hoc values before the vocabulary is defined — making that history unusable
# anyway — while opening a second leak channel beside ``--detail`` for no present
# gain. Adding a flag later is backward-compatible; retracting one is not.

_ALLOWED_PROPERTIES: dict[str, frozenset[str]] = {
    CORE_ACTION_COMPLETED: frozenset({
        "action_name",
        "success",
        "result_count",
        # Two clocks, deliberately not one field. `latency_ms` is memU's own
        # blocking work inside a single process; `duration_ms` is the whole
        # prepare -> commit bridging cycle, which spans two of them and is mostly
        # the agent's. See `_cycle_duration_ms` in `memu.hosts.host_cli`.
        "latency_ms",
        "duration_ms",
        "recall_file_count",
        "resource_count",
        "session_count",
    }),
    # Success-only events (ADR 0016 §4), so there is nothing to say. A constant
    # ``success: true`` would teach a consumer nothing while inviting someone to
    # later "fix" it by sending ``false`` — quietly re-creating the second failure
    # channel the success-only decision removed. The start event carries nothing
    # for the same reason from the other end: it reports that an attempt began,
    # and its existence is the entire signal.
    CLI_INSTALL_STARTED: frozenset(),
    CLI_INSTALL_COMPLETED: frozenset(),
    CLI_UNINSTALLED: frozenset(),
    CORE_ACTION_FAILED: frozenset({"stage", "action_name", "detail"}),
    CLI_ERROR: frozenset({"command", "error_type", "frames", "frames_truncated"}),
    CLI_EVENTS_DROPPED: frozenset({"dropped_count"}),
}
"""Per event, the keys allowed out. Anything else is dropped rather than passed
through — including anything an agent supplied. An allowlist, so adding a leak
takes a deliberate edit."""

AGENT_PLATFORMS: dict[str, str] = {
    # `HostSpec.host` is also the on-disk directory name, so it is not free to
    # change; the mapping happens at the envelope boundary instead.
    "claude-code": "claude_code",
    # The generic adapter's host id is `agent` (its binary is `memu-agent`).
    # "agent" is meaningless as an analytics dimension; ADR 0011's own name for
    # it is the generic adapter.
    "agent": "generic",
}
"""Explicit, not a hopeful string transformation. Anything unlisted falls back to
hyphen-to-underscore, and an absent host (the core ``memu`` binary, which has no
host at all) reports ``none``."""


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #


def _off(value: str | None) -> bool:
    return (value or "").strip().lower() in {"0", "false", "no", "off"}


def _on(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def events_url() -> str | None:
    """The ingest endpoint, or ``None`` when reporting is switched off.

    Read live rather than captured at import, so a test or an air-gapped install
    can steer it per process. Read through :func:`~memu.env.env_declared` and not
    :func:`~memu.env.env`, because the off position is the *empty string* and
    ``env`` would treat that as absent and hand back the default — re-enabling
    exactly what was switched off.
    """
    return env_declared("MEMU_EVENTS_BASE_URL", DEFAULT_EVENTS_URL) or None


def enabled() -> bool:
    """Whether to record and flush at all. Checked first by every entry point."""
    if _off(env_declared("MEMU_TELEMETRY", "1")):
        return False
    # Process environment only: DO_NOT_TRACK is a cross-tool convention, not memU
    # configuration, and a user who exported it has already said this once.
    if _on(os.environ.get("DO_NOT_TRACK")):
        return False
    return events_url() is not None


def _spool_path() -> Path:
    return Path(os.path.expanduser(env("MEMU_EVENTS_SPOOL", SPOOL_PATH) or SPOOL_PATH))


def _config_path() -> Path:
    return Path(os.path.expanduser(os.environ.get("MEMU_CONFIG_ENV", CONFIG_ENV)))


def client_version() -> str:
    """The installed ``memu-cli`` version.

    The Python package's number always wins: ``npm/package.json`` carries its own,
    unrelated version because it is a thin launcher for the PyPI package, so
    ``client_version`` always answers "which memU is running", never "how was it
    fetched".
    """
    from memu import __version__

    return __version__


def client_instance_id() -> str:
    """This machine's stable id, generated once and kept in ``~/.memu/config.env``.

    That file is the right home for one specific reason: ``UNINSTALL.md`` Part 3
    says to keep it **always**, unconditionally, so install → uninstall →
    reinstall joins into one instance's history — which is the whole point of the
    id. The obvious alternative, ``~/.memu/hosts/<host>/``, is exactly what Part 3
    tells the agent to remove, and would additionally fragment one machine into
    one id per host.

    Opaque and random: no hostname, no MAC, no user name. Nothing is derived, so
    nothing can be re-derived, and deleting the line is a complete reset.
    """
    existing = env("MEMU_CLIENT_ID")
    if existing:
        return existing

    generated = str(uuid.uuid4())
    path = _config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        prefix = "" if (not text or text.endswith("\n")) else "\n"
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"{prefix}MEMU_CLIENT_ID={generated}\n")
    except OSError:
        # Unwritable config: still return an id so this run reports, it just will
        # not persist. A machine that cannot write its own config has a larger
        # problem than telemetry continuity.
        return generated

    # Two first runs racing would each append a line. Re-read rather than trust
    # what we just wrote: the parser takes the last assignment, so both processes
    # converge on the same value instead of splitting the machine in two.
    reload()
    return env("MEMU_CLIENT_ID") or generated


def agent_platform(host: str | None) -> str:
    if not host:
        return "none"
    return AGENT_PLATFORMS.get(host, host.replace("-", "_"))


def _os_name() -> str:
    return {"Darwin": "macos", "Windows": "windows", "Linux": "linux"}.get(platform.system(), "other")


def _now() -> str:
    """RFC 3339 UTC with milliseconds.

    Stamped when an event is *recorded*, not when it is sent — with a spool the
    two routinely differ by hours. The backend keeps its own receive time and must
    not treat this as monotone: it is a client clock, and client clocks are wrong.
    """
    now = datetime.now(UTC)
    return f"{now.strftime('%Y-%m-%dT%H:%M:%S')}.{now.microsecond // 1000:03d}Z"


def _session_id(session_id_env: str) -> str:
    """The host session this process is running in, when the host hands it over.

    ADR 0015 already established ``HostSpec.session_id_env``. Where it is set the
    field is filled; where it is not, it is omitted. Nothing is inferred and no
    new survey work is owed — an unsurveyed host simply reports no session.
    """
    if not session_id_env:
        return ""
    return os.environ.get(session_id_env, "").strip()


# --------------------------------------------------------------------------- #
# Recording
# --------------------------------------------------------------------------- #


def envelope(
    event_name: str,
    *,
    host: str = "",
    session_id_env: str = "",
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one event. The single construction site, shared by both transports,
    so :func:`record` and :func:`send_now` cannot drift into different shapes."""
    built: dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "event_name": event_name,
        "client_type": CLIENT_TYPE,
        "client_instance_id": client_instance_id(),
        "client_version": client_version(),
        "agent_platform": agent_platform(host),
        "os": _os_name(),
        "deployment_mode": memory_mode(),
        "occurred_at": _now(),
        "context": {},
        "properties": _filter(event_name, properties),
    }
    session_id = _session_id(session_id_env)
    if session_id:
        # Omitted, never faked, when the host does not hand one over.
        built["session_id"] = session_id
    return built


def record(
    event_name: str,
    *,
    host: str = "",
    session_id_env: str = "",
    properties: dict[str, Any] | None = None,
) -> None:
    """Append one event to the spool. Never sends, never raises.

    The only cost on the per-turn ``retrieve`` path: one ``O_APPEND`` line, no
    network, and no read of the existing spool. Keep it that way — anything that
    makes recording read or rewrite the spool moves cost onto that path.
    """
    try:
        if not enabled():
            return
        built = envelope(event_name, host=host, session_id_env=session_id_env, properties=properties)
        _append(json.dumps(built, ensure_ascii=False, default=str))
    except Exception:
        # Includes a broken MEMU_MEMORY_MODE, which `memory_mode()` raises on.
        # Reporting must not be the thing that surfaces a config error.
        return


def _filter(event_name: str, properties: dict[str, Any] | None) -> dict[str, Any]:
    allowed = _ALLOWED_PROPERTIES.get(event_name, frozenset())
    return {key: value for key, value in (properties or {}).items() if key in allowed}


def _append(line: str) -> None:
    path = _spool_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file() and path.stat().st_size >= MAX_SPOOL_BYTES:
            _count_drop()
            return
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def _drop_counter() -> Path:
    return _spool_path().with_suffix(".dropped")


def _count_drop() -> None:
    """Tally an event the cap discarded, so the loss is reported, not silent."""
    counter = _drop_counter()
    try:
        previous = int(counter.read_text(encoding="utf-8").strip()) if counter.is_file() else 0
    except (OSError, ValueError):
        previous = 0
    with contextlib.suppress(OSError):
        counter.write_text(str(previous + 1), encoding="utf-8")


def record_action(
    action_name: str,
    *,
    host: str = "",
    session_id_env: str = "",
    success: bool,
    **counts: Any,
) -> None:
    """A ``core_action_completed`` — the shape retrieve and remember share."""
    record(
        CORE_ACTION_COMPLETED,
        host=host,
        session_id_env=session_id_env,
        properties={"action_name": action_name, "success": success, **counts},
    )


def record_agent_error(
    *,
    stage: str,
    detail: str = "",
    host: str = "",
    session_id_env: str = "",
) -> None:
    """The agent-reported error: a stage from :data:`STAGES` plus free-form prose.

    In v1 this is *stage plus prose*, so consume it as a triage inbox read by
    humans, not as a metric.

    ``action_name`` is the same string as ``stage``, written at this one site so
    :data:`CORE_ACTION_FAILED` carries the discriminator its ``completed``
    counterpart does. The two fields are one value and stay one value: nothing
    reads ``action_name`` back, and any future rule that would make them differ
    belongs in a mapping here rather than in a caller. What they are *not* is one
    vocabulary — :data:`STAGES` says ``remember``/``retrieve`` where
    :data:`CORE_ACTION_COMPLETED` says ``memory_update``/``memory_search``, so the
    two events do not join on this field as they stand. Deliberate: ``stage`` also
    spans ``install``/``uninstall``/``other``, which name no core action at all,
    and translating the two that do overlap would leave the rest lying.

    Deduplicated on ``(stage, detail)`` for :data:`ERROR_DEDUP_SECONDS`, because an
    agent in a retry loop will otherwise file the same failure a dozen times. The
    ledger that remembers this is a sidecar file rather than the spool: the caller
    flushes inline, so by the next retry the spool is empty and a scan of it would
    call every repeat new. Reading a small file here is affordable in a way it
    would not be in :func:`record` — this path is rare, not per-turn.
    """
    try:
        if not enabled():
            return
        clipped = detail.strip()[:MAX_DETAIL_CHARS]
        if not _claim_error(stage, clipped):
            return
        record(
            CORE_ACTION_FAILED,
            host=host,
            session_id_env=session_id_env,
            properties={"stage": stage, "action_name": stage, "detail": clipped},
        )
    except Exception:
        return


def _error_ledger() -> Path:
    return _spool_path().with_suffix(".errors")


def _claim_error(stage: str, detail: str) -> bool:
    """Whether this failure is new — and if so, remember it.

    Fingerprints rather than the pair itself, so the ledger is bounded no matter
    how long a ``--detail`` is and so the one file this module keeps *outside* the
    spool holds no agent prose. It never leaves the machine either way; a hash
    simply gives it nothing to leak.

    Fails open like everything else here: an unwritable ledger costs duplicate
    events, never a lost one.
    """
    ledger = _error_ledger()
    fingerprint = hashlib.sha256(f"{stage}\x00{detail}".encode()).hexdigest()[:16]
    now = datetime.now(UTC).timestamp()
    kept = [entry for entry in _read(ledger) if now - _stamp(entry) < ERROR_DEDUP_SECONDS]
    if any(entry.get("fingerprint") == fingerprint for entry in kept):
        return False
    _retain(ledger, [*kept[-(MAX_LEDGER_ENTRIES - 1) :], {"fingerprint": fingerprint, "at": now}])
    return True


def _stamp(entry: dict[str, Any]) -> float:
    """A ledger entry's age basis. An unparseable stamp reads as ancient, so a
    corrupted line expires rather than deduplicating forever."""
    at = entry.get("at")
    return float(at) if isinstance(at, (int, float)) else 0.0


def record_cli_error(exc: BaseException, *, command: str = "", host: str = "", session_id_env: str = "") -> None:
    """The code-observed error, from the CLI's top-level handler.

    No model is in the loop, so the data is exact — and that is also why the
    payload needs care. A rendered traceback is **not** sendable: absolute paths
    carry the OS username and often the user's project names. So frames are
    reduced to ``module:function:lineno``, with the module as a dotted path and
    never a filesystem path, and the exception *message* is omitted entirely —
    messages are where secrets and paths actually surface (a ``ConfigError``
    naming a DSN, an HTTP error echoing a URL with a token).
    """
    try:
        frames = _frames(exc)
        record(
            CLI_ERROR,
            host=host,
            session_id_env=session_id_env,
            properties={
                "command": command,
                "error_type": type(exc).__name__,
                "frames": frames[-MAX_FRAMES:],
                "frames_truncated": len(frames) > MAX_FRAMES,
            },
        )
    except Exception:
        return


def _frames(exc: BaseException) -> list[str]:
    labels: list[str] = []
    for frame in traceback.extract_tb(exc.__traceback__):
        labels.append(f"{_module_of(frame.filename)}:{frame.name}:{frame.lineno}")
    return labels


def _module_of(filename: str) -> str:
    """A dotted module path, or ``<external>``. Never a filesystem path.

    Anything outside the ``memu`` package is collapsed rather than reported:
    a site-packages path is harmless, but a path through the user's own
    checkout is not, and telling them apart reliably is not worth the risk.
    """
    parts = Path(filename).with_suffix("").parts
    if "memu" not in parts:
        return "<external>"
    start = len(parts) - 1 - parts[::-1].index("memu")
    return ".".join(parts[start:])


# --------------------------------------------------------------------------- #
# Delivery
# --------------------------------------------------------------------------- #


def flush() -> tuple[int, int]:
    """Deliver everything spooled, as ``(accepted, rejected)``.

    Called from the latency-tolerant places only: ``prepare`` and ``commit``,
    ``report uninstall`` (which cannot wait — ``UNINSTALL.md`` Part 3 may remove
    the very binary that would flush later), the explicit ``report flush``, and
    the CLI's error handler.

    Never raises. A failed POST leaves its file in place for the next flush.
    """
    try:
        return _flush()
    except Exception:
        return (0, 0)


def _flush() -> tuple[int, int]:
    if not enabled():
        return (0, 0)
    url = events_url()
    if url is None:
        return (0, 0)
    _promote_drop_counter()
    accepted = rejected = 0
    posts_left = MAX_FLUSH_POSTS
    for path in _pending():
        events = _read(path)
        if not events:
            _unlink(path)
            continue
        index = 0
        stalled = False
        while index < len(events):
            if posts_left <= 0:
                # Out of budget, not broken: the tail is retained and the next
                # flush picks up exactly where this one stopped.
                stalled = True
                break
            outcome = _post(url, events[index])
            posts_left -= 1
            if outcome == RETRY:
                # Left at `index`, so the event that failed is the first one
                # retried rather than being counted as delivered.
                stalled = True
                break
            index += 1
            if outcome == ACCEPTED:
                accepted += 1
            else:
                rejected += 1
        if stalled:
            _retain(path, events[index:])
            break
        _unlink(path)
    return (accepted, rejected)


def _pending() -> list[Path]:
    """Files to deliver: any orphaned from a crashed flush, then the live spool.

    Rotating the spool with :func:`os.replace` is what makes a shared spool safe:
    concurrent appends land in a fresh file, and a flush that dies leaves a
    ``.sending`` file the next one picks up.
    """
    spool = _spool_path()
    files = sorted(spool.parent.glob(f"{spool.name}.*.sending")) if spool.parent.is_dir() else []
    with contextlib.suppress(OSError):
        if spool.is_file() and spool.stat().st_size:
            target = spool.parent / f"{spool.name}.{uuid.uuid4().hex}.sending"
            os.replace(spool, target)
            files.append(target)
    return files


def _promote_drop_counter() -> None:
    """Turn a pending drop tally into a real event, so the loss is reported."""
    counter = _drop_counter()
    try:
        dropped = int(counter.read_text(encoding="utf-8").strip()) if counter.is_file() else 0
    except (OSError, ValueError):
        dropped = 0
    if dropped <= 0:
        return
    try:
        counter.unlink(missing_ok=True)
    except OSError:
        return
    record(CLI_EVENTS_DROPPED, properties={"dropped_count": dropped})


def _read(path: Path) -> list[dict[str, Any]]:
    """Parse a spool file, skipping unparseable lines.

    A truncated final line — the signature of a process killed mid-append — must
    cost that one event, never the file.
    """
    events: list[dict[str, Any]] = []
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return events
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def _unlink(path: Path) -> None:
    with contextlib.suppress(OSError):
        path.unlink(missing_ok=True)


def _retain(path: Path, events: list[dict[str, Any]]) -> None:
    """Rewrite *path* to hold exactly *events* — the one writer for every file this
    module replaces wholesale, the spool tail and the dedup ledger alike.

    For a flush it leaves only the undelivered tail behind, so the next one resumes
    instead of re-posting what this one already delivered.

    Without this a spool longer than :data:`MAX_FLUSH_POSTS` never drains: every
    flush would spend its whole budget on the same leading events and stop in the
    same place. Written via a temporary file and :func:`os.replace` so a crash
    mid-rewrite cannot leave a half-written spool. If the rewrite fails the file
    is left whole — the next flush re-posts and ``event_id`` deduplicates, which
    is the same bargain the retry path already makes.
    """
    lines = "".join(json.dumps(event, ensure_ascii=False, default=str) + "\n" for event in events)
    temp = path.parent / f"{path.name}.partial"
    try:
        temp.write_text(lines, encoding="utf-8")
        os.replace(temp, path)
    except OSError:
        _unlink(temp)


def _headers() -> dict[str, str]:
    """The ingest endpoint needs no authentication; the backend owns abuse control.

    So the rule is exactly: send the key if one happens to exist, omit the header
    otherwise. Local-mode users, who have no key at all, are first-class.

    Read through :func:`env` and not ``env.cloud_api_key()`` — the latter *raises*
    when unset, which is right for its own caller and exactly wrong here.

    ``User-Agent`` is not decoration and must not be dropped as noise. Left unset,
    ``urllib`` sends ``Python-urllib/<version>``, which the CDN in front of the
    ingest host blocks outright — every POST comes back ``403`` with Cloudflare
    error 1010, before the endpoint is ever reached. Since :func:`_post` reads a
    permanent 4xx as "the server will never take this" and discards the batch,
    the failure mode was total silent event loss on a fail-open path: nothing
    logged, nothing retried, nothing delivered.
    """
    headers = {
        "Content-Type": "application/json",
        "User-Agent": f"memu-cli/{client_version()}",
    }
    key = env("MEMU_CLOUD_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


ACCEPTED, REJECTED, RETRY = "accepted", "rejected", "retry"
"""What became of one event. ``REJECTED`` is distinct from ``ACCEPTED`` on
purpose: both mean "stop holding this", but only one means the backend has the
data, and collapsing them would let a server rejecting *everything* report itself
as healthy delivery — the precise class of invisible failure this module exists
to end."""


def _post(url: str, event: dict[str, Any]) -> str:
    """POST one event, returning one of :data:`ACCEPTED` / :data:`REJECTED` / :data:`RETRY`.

    One event per request, because that is what the endpoint accepts: its schema
    validates the body as a single envelope object, and a JSON array comes back
    ``422 "Input should be an object"``. Sending a batch would be discarded as a
    permanent 4xx — the whole batch, silently.

    Provisional. Batching is the shape this client wants and :data:`MAX_FLUSH_POSTS`
    is sized on the assumption it returns; whether the endpoint grows an array form
    is the backend team's call, and until they make it the client matches what is
    deployed rather than what it would prefer.

    Blocking, on a short timeout, using ``urllib`` for the same reason
    :mod:`memu.hosts.templates` does: this must not depend on the async stack or
    on an HTTP client's configuration to stay fail-open.
    """
    body = json.dumps(event, ensure_ascii=False, default=str).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=_headers(), method="POST")  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:  # noqa: S310
            return ACCEPTED if 200 <= getattr(response, "status", 200) < 300 else RETRY
    except urllib.error.HTTPError as exc:
        # A permanent 4xx means the server will reject this payload every time;
        # retrying forever would pin the spool and eventually hit the cap, so
        # these are discarded. 429 is not permanent — that one waits.
        return REJECTED if 400 <= exc.code < 500 and exc.code != 429 else RETRY
    except Exception:
        return RETRY


def send_now(
    event_name: str,
    *,
    host: str = "",
    session_id_env: str = "",
    properties: dict[str, Any] | None = None,
) -> bool:
    """Deliver one event immediately, bypassing the spool.

    **Not in use.** No caller exists, by decision (ADR 0016 §2): the spool is the
    active path, and ``report uninstall`` — the one event that cannot wait —
    triggers an ordinary inline :func:`flush` rather than this.

    It is written now so the transport seam is proven to admit both modes and
    turning it on later stays a one-line change instead of a refactor. Enabling it
    for a given event is a future decision that must state why that event cannot
    tolerate spool latency; it blocks the calling command for up to
    :data:`_TIMEOUT_SECONDS`, which is why ``retrieve`` will never be that event.
    """
    try:
        if not enabled():
            return False
        url = events_url()
        if url is None:
            return False
        built = envelope(event_name, host=host, session_id_env=session_id_env, properties=properties)
        return _post(url, built) == ACCEPTED
    except Exception:
        return False


def counts(result: dict[str, Any], layers: Iterable[str] = ("segments", "files", "resources")) -> int:
    """Total hits across a retrieval result's layers — the ``result_count`` field."""
    return sum(len(result.get(layer, []) or []) for layer in layers)
