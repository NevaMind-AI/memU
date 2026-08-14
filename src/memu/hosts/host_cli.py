"""One command surface, many host binaries.

Every host adapter exposes the same verbs — ``retrieve``, ``install-instruction``,
``remove-instruction``, ``prepare``, ``commit``, ``verify-resources``, ``doctor``,
``docs`` — because the
pipeline behind them is host-agnostic (ADR 0008/0009). What differs per host is
data, not code: the binary's name, where the session log lives, which file the
standing instruction lands in, and the packaged guides. So the parser is built
once here from a :class:`HostSpec`, and each host's ``cli.py`` shrinks to that
declaration plus a ``main``.

Working state is per host. Codex predates this module and keeps its original
``~/.memu`` working tree; every later host defaults to ``~/.memu/hosts/<host>``,
so two hosts' bridging runs never race over one ``jobs/`` directory (the open
issue ADR 0009 required settling before a second host shipped — see ADR 0010).
The durable backend is shared regardless: every host reads
``~/.memu/config.env``, which is the point — what one host's sessions taught
memU, another host retrieves.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import platform
import sys
import time
import urllib.request
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from typing import Any, Literal

from memu import events
from memu.hosts import instruction, retrieval, templates
from memu.hosts.base import TranscriptSource
from memu.hosts.bridging import Layout, commit, prepare, self_sessions
from memu.hosts.bridging.pipeline import MAX_JOBS
from memu.hosts.bridging.resources import verify_resource_log

ScheduleBackend = Literal["os", "native", "external"]
"""The existing scheduler arrangement a host documents; informational only."""

DOCS = {"install": "INSTALL.md", "task": "BRIDGING_TASK.md", "uninstall": "UNINSTALL.md"}


@dataclass(frozen=True)
class HostSpec:
    """Everything host-specific about a host adapter's CLI — data, not code."""

    host: str
    """Short host id (``codex``). Names the binary and scopes the working tree."""

    display: str
    """Human name used in help text (``Codex``)."""

    package: str
    """Dotted package holding the host's ``INSTALL.md`` / ``BRIDGING_TASK.md``."""

    source_factory: Callable[[str], TranscriptSource]
    """Builds the host's :class:`TranscriptSource` from the ``--session-dir`` value."""

    session_dir: str
    """Default location of the host's session log (dir, or file for SQLite hosts)."""

    session_help: str
    """What the session log is, for ``--session-dir``'s help text."""

    instruction_path: str
    """The host's global instruction file — where the inject seam lands."""

    legacy_instruction_paths: tuple[str, ...] = ()
    """Previous default instruction files to unpatch after installing the current
    target, and to inspect during uninstall. Only used when the CLI's default
    ``--path`` is in effect, so an explicit custom target never rewrites unrelated
    files. This is an upgrade seam, not a second active instruction location."""

    skills_dir: str = ""
    """The host's skills directory, for hosts that have skills (``~/.codex/skills``,
    ``~/.claude/skills``). Given one, ``install-instruction`` puts the retrieval
    procedure in a skill there and leaves only a pointer in ``instruction_path``.
    Empty — the default, and every host without a skills mechanism — keeps the full
    text inline, which is the only place it can live."""

    base_dir: str = ""
    """memU working tree. Empty means the per-host default ``~/.memu/hosts/<host>``;
    Codex overrides this with the pre-multi-host ``~/.memu`` it has always used."""

    schedule_backend: ScheduleBackend = "external"
    """The host's documented scheduler arrangement.

    Informational metadata only: it never controls task registration, scheduler
    invocation, or which CLI commands are available.
    """

    schedule_command: str = ""
    """The headless agent invocation the Windows Task Scheduler helper runs, as a
    template with a ``{prompt}`` placeholder — ``claude -p {prompt}``. The helper
    turns this into the scheduled task's wrapper, asks Windows PowerShell itself
    to resolve the first token exactly as it does for the user, and exposes the
    ``schedule`` subcommand only when it is set. Empty means that helper is not
    wired for this host; Unix scheduling remains doc-driven and never reads this
    field.
    """

    schedule_prepare_session_dir: bool = False
    """Bake this host's resolved ``session_dir`` into the scheduled PREPARE command.

    Most hosts have one stable conventional path and need no explicit flag. Hosts
    whose store moves with a runtime home (Hermes's ``HERMES_HOME``) opt in so the
    S4U task is independent of which environment variables it inherits."""

    schedule_prompt_stdin: bool = False
    """Pipe the scheduled prompt to the agent's stdin and replace ``{prompt}``
    with ``-`` in the argv.

    This is host capability data, not a shell workaround guessed by the shared
    scheduler. Codex documents ``-`` as "read instructions from stdin", which
    avoids Windows PowerShell 5.1 re-splitting a long prompt when an npm ``.ps1``
    shim forwards its argument list. Hosts whose one-shot command requires a
    prompt argument keep the default.
    """

    session_id_env: str = ""
    """Environment variable through which the host tells a tool subprocess which
    session it is running in (``CLAUDE_CODE_SESSION_ID``). It answers *which*
    session, never *whether* to claim one: only a run that
    :func:`~memu.hosts.bridging.self_sessions.is_bridging_run` recognises as the
    scheduled one reads it at all, so a person running ``prepare`` by hand keeps
    their conversation mineable (#606). An exact identity, never a guess about
    content. Its value must match what
    :meth:`~memu.hosts.base.TranscriptSource.session_id` derives from a discovered
    session. Empty — the default — means the host has not been surveyed yet, and
    the run keeps mining itself as before."""

    needs_headless_auth: bool = False
    """Whether the scheduled agent needs a headless credential distinct from any
    desktop login (memU#538 Symptom B). True for ``claude-code`` — the Desktop
    app's login is invisible to the standalone CLI; False for hosts with a shared
    plain-file auth (Codex's ``~/.codex/auth.json``). Drives whether ``schedule``
    runs the ``-p`` authentication gate before registering the task."""

    install_hint: str = ""
    """Copy-pasteable command(s) for installing this host's standalone CLI on
    Windows, shown when ``schedule install`` finds it missing (memU#538 Symptom A).
    Host-specific data, so the shared installer never hardcodes one host's package
    names; empty falls back to generic guidance."""

    auth_hint: str = ""
    """How to give this host's CLI a usable headless credential, shown when the
    ``schedule`` auth gate fails (memU#538 Symptom B). Host-specific data for the
    same reason as ``install_hint`` — claude's remedy is ``setup-token``, cursor's
    is the signed-in IDE account session; the shared gate must not prescribe one
    host's fix for another's failure. Empty falls back to generic guidance."""

    extra_flags: dict[str, str] = field(default_factory=dict)
    """Reserved for host-specific flags; unused today."""

    register_extra: Callable[[Any], None] | None = None
    """Optional hook adding host-specific subcommands (the generic adapter's
    ``detect``). Called with the subparsers object after the shared verbs."""

    resolve_self_sessions: Callable[[TranscriptSource, Layout], list[str]] | None = None
    """Optional native-scheduler identity resolver.

    OS-scheduled hosts use ``session_id_env`` plus the shared launch marker.
    Native schedulers can instead resolve their registered task from structural
    host metadata, without asking the model to carry identity.
    """

    @property
    def binary(self) -> str:
        return f"memu-{self.host}"

    @property
    def verify_command(self) -> str:
        """What the resource job tells the agent to run. A command, never a path."""
        return f"{self.binary} verify-resources"

    @property
    def default_base_dir(self) -> str:
        return self.base_dir or f"~/.memu/hosts/{self.host}"

    @property
    def task_name(self) -> str:
        """Canonical scheduled-task name — stable across install/uninstall so the
        task is addressable by name (memU#539). Windows only today; Unix keeps its
        existing crontab/launchd identity untouched."""
        return f"memu-bridging-{self.host}"


def _layout(spec: HostSpec, args: argparse.Namespace) -> Layout:
    return Layout.default(host=spec.host, base=args.base_dir)


def _refresh_retrieval(spec: HostSpec) -> None:
    """Piggyback the retrieval-procedure refresh on the scheduled prepare.

    The retrieval body self-updates from the server on this low-frequency run
    instead of on the per-turn retrieve hook (ADR 0013). That the hook now spends
    one bounded POST reporting its own event (ADR 0016 §2) does not open a door
    here: this fetch is a document download whose size and count are the server's
    to decide, which is a different proposition from one fixed envelope. Best-effort
    and firewalled: any failure here is a note, never a failed bridging run — and
    :func:`instruction.refresh` skips (rather than downgrades) when the server is
    unreachable, so a note here means the installed copy simply stayed put.
    """
    skills_dir = Path(spec.skills_dir) if spec.skills_dir else None
    try:
        for target, changed in instruction.refresh(Path(spec.instruction_path), spec.binary, skills_dir=skills_dir):
            if changed:
                print(f"refreshed the retrieval procedure at {target}")
    except Exception as exc:
        print(f"note: could not refresh the retrieval procedure ({exc})", file=sys.stderr)


async def _cmd_prepare(spec: HostSpec, args: argparse.Namespace) -> int:
    source = spec.source_factory(args.session_dir)
    if not source.exists():
        print(f"error: no {spec.display} session log at {source.root()}", file=sys.stderr)
        return 2

    layout = _layout(spec, args)
    _mark_cycle_start(spec, layout)
    # This run is itself a host session, and the host is logging it where we are
    # about to look. Remember it now — before the scan — so it is skipped by this
    # run and every later one (#606).
    own_session = os.environ.get(spec.session_id_env, "").strip() if spec.session_id_env else ""
    skip_sessions = (
        spec.resolve_self_sessions(source, layout)
        if spec.resolve_self_sessions is not None
        else self_sessions.load(layout.self_sessions)
    )
    # Only the *scheduled* run may claim a session. A person running prepare by
    # hand is asking for the current conversation to be mined, so claiming it
    # there would deliver the exact opposite, permanently.
    if not self_sessions.is_bridging_run(Path.cwd(), layout.base):
        own_session = ""
    elif spec.session_id_env and not own_session:
        # The host advertised a variable and did not set it — a headless runner
        # that lost it, or a version that dropped it. Say so: the alternative is
        # #606 quietly returning while everything still looks healthy.
        print(
            f"warning: {spec.session_id_env} is unset, so this run cannot recognise its own"
            " session; it will be mined like any other",
            file=sys.stderr,
        )
    if own_session and own_session not in skip_sessions:
        # Also fires when a human runs `prepare` inside a real conversation, and
        # that session is then excluded from mining for good — so it must never
        # happen silently.
        print(
            f"note: recording this session ({own_session}) as a bridging run; its transcript "
            f"will not be mined. Undo by removing it from {layout.self_sessions}"
        )
    if own_session:
        skip_sessions = self_sessions.remember(layout.self_sessions, own_session)
    num_sessions = await prepare(
        source,
        layout,
        verify_command=spec.verify_command,
        max_jobs=args.max_jobs,
        skip_sessions=skip_sessions,
        # Carried purely so the `memory_list` event the store mirror records can
        # name its platform and session, the same two strings `retrieve` carries.
        host=spec.host,
        session_id_env=spec.session_id_env,
    )
    num_jobs = 2 * num_sessions + 1
    print(f"prepared {num_sessions} session(s) -> {num_jobs} job(s) in {layout.jobs}")
    if num_sessions == 0:
        print("no new session turns since the last run; nothing to mine")
    _refresh_retrieval(spec)
    # One of the two designated flush points (ADR 0016): low-frequency and
    # latency-tolerant, which is exactly what the per-turn retrieve hook is not.
    events.flush()
    return 0


async def _cmd_commit(spec: HostSpec, args: argparse.Namespace) -> int:
    # The terminal step of the record seam, so this is where the remember event
    # belongs — and it already holds the counts that event reports.
    layout = _layout(spec, args)
    session_count = _pending_session_count(layout)
    started = time.monotonic()
    try:
        result = await commit(layout)
    except Exception:
        _record_commit(
            spec,
            layout,
            success=False,
            recall_files=0,
            resources=0,
            sessions=session_count,
            latency_ms=_elapsed_ms(started),
        )
        raise
    recall_files = result.get("recall_files", [])
    resources = result.get("resources", [])
    _record_commit(
        spec,
        layout,
        success=True,
        recall_files=len(recall_files),
        resources=len(resources),
        sessions=session_count,
        latency_ms=_elapsed_ms(started),
    )
    # The cycle is closed and reported, so the marker has done its job. Cleared
    # only on the success path — the `raise` above keeps it, so a retried commit
    # still measures from the prepare that actually opened this cycle rather than
    # reporting nothing.
    with contextlib.suppress(OSError):
        layout.run_marker.unlink(missing_ok=True)
    events.flush()
    if not recall_files and not resources:
        print("nothing to commit")
        return 0
    print(f"committed {len(recall_files)} recall file(s) and {len(resources)} resource(s)")
    for recall_file in recall_files:
        print(f"  - {recall_file.get('track')}/{recall_file.get('name')}")
    return 0


def _pending_session_count(layout: Layout) -> int:
    """How many session slices this run mined, read before ``commit`` clears them.

    A count, never a name: which sessions were mined is content, and content does
    not leave the machine (ADR 0016 §10).
    """
    try:
        return len(list(layout.sessions.glob("*.jsonl")))
    except OSError:
        return 0


MAX_CYCLE_SECONDS = 24 * 60 * 60
"""Past this a reported cycle is not believed. See :func:`_cycle_duration_ms`."""


def _elapsed_ms(started: float) -> int:
    """Milliseconds since a :func:`time.monotonic` reading."""
    return round((time.monotonic() - started) * 1000)


def _mark_cycle_start(spec: HostSpec, layout: Layout) -> None:
    """Stamp when this bridging cycle began, for ``commit`` to close, and report it.

    Wall clock, unavoidably: the two halves of the record seam are separate
    processes and no monotonic clock survives that boundary. What follows from
    that is handled where the stamp is read, in :func:`_cycle_duration_ms`.

    Overwritten by every ``prepare``, which is the right reading of a second one:
    it regenerated the job files, so the cycle the agent is working is the one
    that starts here. Best-effort like everything on the reporting path — an
    unwritable marker costs the field, never the run.

    ``memory_update_started`` is emitted here rather than at the call site, and only
    when the marker actually landed, because the marker is what lets ``commit``
    emit the matching ``memory_update_succeeded`` (:func:`_record_commit`). Announcing
    a cycle this machine cannot later close would manufacture a failure out of a
    full disk — the two must not be able to disagree, so one function owns both.
    """
    try:
        layout.run_marker.parent.mkdir(parents=True, exist_ok=True)
        layout.run_marker.write_text(json.dumps({"started_at": time.time()}), encoding="utf-8")
    except OSError:
        return
    events.record(events.MEMORY_UPDATE_STARTED, host=spec.host, session_id_env=spec.session_id_env)


def _cycle_duration_ms(layout: Layout) -> int | None:
    """How long the whole cycle took, ``prepare`` to here — or ``None``.

    Not a latency, and it must not be read as one. Most of this number is the
    agent's self-evolve pass *between* the two commands — reading transcripts,
    writing markdown — so it measures the bridging round trip, not memU's work.
    ``latency_ms`` beside it is the part that is memU's.

    Being wall clock (see :func:`_mark_cycle_start`), a suspended laptop or an
    NTP step lands inside it too. So the impossible is dropped rather than sent:
    a negative span means the clock moved backwards, and one longer than
    :data:`MAX_CYCLE_SECONDS` is a machine that slept through a week, not a slow
    agent. ``None`` — an absent field, never a zero — is also the honest answer
    when there is no marker at all: a ``commit`` with no preceding ``prepare``, or
    an upgrade that landed mid-cycle. A row a consumer can exclude, rather than
    one that silently poisons an average.
    """
    try:
        started = json.loads(layout.run_marker.read_text(encoding="utf-8"))["started_at"]
        elapsed = time.time() - float(started)
    except (OSError, ValueError, TypeError, KeyError):
        return None
    if not 0 <= elapsed <= MAX_CYCLE_SECONDS:
        return None
    return round(elapsed * 1000)


def _cycle_is_open(layout: Layout) -> bool:
    """Whether this ``commit`` is closing a cycle a ``prepare`` here opened.

    Deliberately *not* "did :func:`_cycle_duration_ms` return a number". The two read
    the same marker and answer different questions: a cycle whose clock skewed, or
    which outlived :data:`MAX_CYCLE_SECONDS`, still happened and still deserves its
    event — it simply reports no duration.
    """
    try:
        return layout.run_marker.is_file()
    except OSError:
        return False


def _record_commit(
    spec: HostSpec,
    layout: Layout,
    *,
    success: bool,
    recall_files: int,
    resources: int,
    sessions: int,
    latency_ms: int,
) -> None:
    """The commit store call — and, when it closed one, the cycle around it.

    Two events over two spans (ADR 0016 §4). ``memory_commit_*`` is *this call*: one
    process, one store round trip, and ``latency_ms`` is memU's own blocking work in
    it. ``memory_update_succeeded`` is the whole ``prepare`` → ``commit`` cycle,
    mostly the agent's self-evolve pass, carrying ``duration_ms`` instead.

    **The cycle event is gated on the run marker.** ``BRIDGING_TASK.md``'s LEFTOVERS
    step commits a crashed run's jobs with no ``prepare`` of its own, so that commit
    closes no cycle and must not report one — otherwise a single bridging run emits
    one start and two successes, and ``started >= succeeded`` stops holding on
    exactly the runs already in trouble. Its counts are still reported, on the commit
    event, which is the only place a leftover's output is ever visible.

    Nothing reports a *failed* cycle from here. A failed commit keeps the marker for
    the retry, so the cycle is not over; ``memory_update_failed`` is agent-reported
    (§5), because a cycle can also die where no code is watching at all.
    """
    counts: dict[str, Any] = {
        "recall_file_count": recall_files,
        "resource_count": resources,
        "session_count": sessions,
    }
    events.record_outcome(
        events.MEMORY_COMMIT_SUCCEEDED,
        events.MEMORY_COMMIT_FAILED,
        host=spec.host,
        session_id_env=spec.session_id_env,
        success=success,
        latency_ms=latency_ms,
        **counts,
    )
    if not success or not _cycle_is_open(layout):
        return
    duration_ms = _cycle_duration_ms(layout)
    if duration_ms is not None:
        # Omitted rather than zeroed when the cycle could not be measured — the
        # distinction is the whole point of `_cycle_duration_ms` returning None.
        counts["duration_ms"] = duration_ms
    events.record(
        events.MEMORY_UPDATE_SUCCEEDED,
        host=spec.host,
        session_id_env=spec.session_id_env,
        properties=counts,
    )


async def _cmd_verify_resources(spec: HostSpec, args: argparse.Namespace) -> int:
    layout = _layout(spec, args)
    kept = verify_resource_log(layout.resource_log, layout.resources)
    print(f"{kept} resource(s) written to {layout.resources}")
    return 0


_TRANSPORT_SMELLS = ("502", "503", "504", "timeout", "timed out", "connect", "unreachable", "proxy")


def _smells_like_transport(exc: BaseException) -> bool:
    """Gate the proxy hint on transport-shaped failures only.

    A missing ``MEMU_DB`` or a 401 from a placeholder key has nothing to do
    with proxies — a hint there would be exactly the misdirection it exists to
    prevent, and on a machine with a VPN-managed system proxy (where proxies
    are *always* detected) it would fire on every failure. Walks the cause
    chain because the interesting error (``ConnectError``, a 502 status) is
    usually wrapped by the SDK before doctor sees it.
    """
    from memu.env import ConfigError

    seen: list[BaseException] = []
    current: BaseException | None = exc
    while current is not None and current not in seen:
        seen.append(current)
        current = current.__cause__ or current.__context__
    if any(isinstance(e, ConfigError) for e in seen):
        return False
    for e in seen:
        text = f"{type(e).__name__} {e}".lower()
        if any(smell in text for smell in _TRANSPORT_SMELLS):
            return True
    return False


def _proxy_hint(base_url: str) -> str | None:
    """One diagnostic line for a failed doctor that smells like proxy trouble.

    The facts that took a live install minutes of tool calls to assemble — the
    target is loopback, the call failed, a proxy is configured (possibly only
    in the OS's system-wide settings, invisible to ``env``) — are all free to
    check right here. So check them and say what they imply, instead of
    leaving the next agent to re-derive the same conclusion from a bare 502.
    """
    proxies = urllib.request.getproxies()
    if not proxies:
        return None
    from memu.embedding.http_client import is_loopback_url

    listing = ", ".join(sorted(set(proxies.values())))
    env_configured = any(k.lower().endswith("_proxy") for k in os.environ)
    source = "the shell environment" if env_configured else "the OS's system-wide settings (invisible to `env`)"

    if not is_loopback_url(base_url):
        return (
            f"hint: requests to this target go through a proxy ({listing}, from {source}). If the target "
            "is actually this machine reached through a non-loopback address (host.docker.internal, a LAN "
            "IP, a WSL/VM host address), the proxy cannot reach it — add that address to NO_PROXY."
        )
    if os.environ.get("MEMU_HTTP_PROXY"):
        return (
            "hint: the embedding target is this machine, and your explicit MEMU_HTTP_PROXY routes memU's "
            "traffic through a proxy anyway. If that proxy cannot reach your localhost, unset MEMU_HTTP_PROXY."
        )
    return (
        f"hint: the embedding target is this machine and a proxy is configured ({listing}, from {source}). "
        "This memU bypasses proxies for loopback targets, so the proxy is likely not the cause — check the "
        f"embedding server itself (is it running? does `curl {base_url}` answer?). On older memU releases "
        "the proxy *would* hijack this call; there, set NO_PROXY=localhost,127.0.0.1."
    )


async def _cmd_doctor(spec: HostSpec, args: argparse.Namespace) -> int:
    """Prove config resolves and the selected backend answers.

    Deliberately exercises the same call the inject hook will, so a green doctor
    means the hook's retrieval works, not merely that some local store opened.
    """
    from memu.env import CONFIG_ENV, cloud_base_url, embedding_provider, env, memory_mode

    try:
        mode = memory_mode()
        result = await retrieval.retrieve("smoke test")
    except Exception as exc:
        if os.environ.get("MEMU_DEBUG") == "1":
            raise
        print(f"error: {exc} (set MEMU_DEBUG=1 for a traceback)", file=sys.stderr)
        if _smells_like_transport(exc):
            try:
                target = cloud_base_url() if memory_mode() == "cloud" else (env("MEMU_BASE_URL", "") or "")
            except Exception:
                target = ""
            hint = _proxy_hint(target)
            if hint:
                print(hint, file=sys.stderr)
        return 1
    found = sum(len(result.get(layer, [])) for layer in ("segments", "files", "resources"))
    print(f"config    {os.path.expanduser(CONFIG_ENV)}")
    print(f"mode      {mode}")
    if mode == "cloud":
        print(f"endpoint  {cloud_base_url()}")
        print("resources accepted but not currently persisted by memU Cloud")
    else:
        print(f"store     {env('MEMU_DB')}")
        print(f"provider  {embedding_provider()}")
    print(f"retrieval ok ({found} hit(s) for a smoke-test query; 0 is fine on a new store)")
    return 0


async def _cmd_docs(spec: HostSpec, args: argparse.Namespace) -> int:
    # Server-first, then last-good cache, then the embedded floor — the same
    # self-updating shape ADR 0013 gives the instruction templates, applied to the
    # host guides. `docs task` prints the guide named BRIDGING_TASK.md; the doc key
    # ("task") and its filename differ, and both the URL and cache key off the
    # filename so the server layout mirrors the package layout.
    filename = DOCS[args.doc]
    embedded = (files(spec.package) / filename).read_text(encoding="utf-8")
    print(templates.resolve_doc(spec.host, filename, embedded))
    if args.doc == "install":
        _report_install_started(spec)
    return 0


def _report_install_started(spec: HostSpec) -> None:
    """The install funnel's entry point (ADR 0016 §4).

    Printing this guide is the first act on the install path that *proves*
    ``memu-cli`` is installed and resolving — `SKILL.md` Step 3, immediately after
    the pip install — so the start is observed here rather than asked for in prose.
    That is what makes ``started >= completed`` hold structurally: ``report
    install`` is voluntary and undercounts, and a start that undercounted
    independently of it could report more completions than attempts.

    ``install-instruction`` was rejected as a stand-in for *completion* precisely
    because it also runs on re-runs and partial repairs. For a *start* that is the
    correct reading: a re-run is a new attempt.

    Flushed, not merely recorded, and that is the load-bearing half. An install
    that dies in Part 2 never reaches ``prepare`` or ``commit`` — the ordinary
    flush points — so without this its start, and every ``cli_error`` it collected
    on the way down, would sit in the spool forever. That run is the exact one
    this event exists to make visible. Affordable here because ``resolve_doc``
    above has already blocked on a server GET: this is a guide-printing path, not
    a hot one.
    """
    events.record(events.CLI_INSTALL_STARTED, host=spec.host, session_id_env=spec.session_id_env)
    events.flush()


async def _cmd_schedule(spec: HostSpec, args: argparse.Namespace) -> int:
    """Register/inspect the existing OS-scheduled bridging task on Windows Task Scheduler.

    The parser registers this handler only when ``schedule_command`` supplies an
    invocation for the Windows helper. ``schedule_backend`` is informational and
    does not affect this behavior. On macOS/Linux, this points at the existing
    cron/launchd registration in ``BRIDGING_TASK.md`` and touches neither.
    """
    system = platform.system()
    if system != "Windows":
        print(
            f"{spec.display} bridging on {system or 'this OS'} is scheduled with cron or launchd — "
            f"follow that section of `{spec.binary} docs task`. The `schedule` helper automates "
            "Windows Task Scheduler only."
        )
        return 0

    from memu.hosts import scheduling

    layout = _layout(spec, args)
    if args.action == "install":
        return scheduling.install(spec, layout, interval_minutes=args.interval)
    if args.action == "uninstall":
        return scheduling.uninstall(spec, layout)
    if args.action == "status":
        return scheduling.status(spec, layout)
    return scheduling.verify(spec, layout)


async def _cmd_report(spec: HostSpec, args: argparse.Namespace) -> int:
    """The one command surface for events code cannot observe by itself (ADR 0016).

    ``install`` and ``uninstall`` exist because those procedures are agent-driven
    prose: ``INSTALL.md`` is a multi-part guide with verify gates and no single
    command spans it, so only the agent knows it reached the final one. Both
    report **success only** — the event's existence is the signal, and failure has
    exactly one channel, ``report error``.

    Only the *completion* needs a verb. The matching start is code-observed in
    :func:`_report_install_started`, because a funnel whose two ends are both
    voluntary can report more completions than attempts.
    """
    # Said plainly rather than silently: a user who switched reporting off should
    # see that this command did nothing, not a "recorded" that is not true.
    outcome = "recorded" if events.enabled() else "reporting is off; nothing recorded"

    if args.what == "install":
        events.record(events.CLI_INSTALL_SUCCEEDED, host=spec.host, session_id_env=spec.session_id_env)
        print(outcome)
        return 0

    if args.what == "uninstall":
        events.record(events.CLI_UNINSTALL_SUCCEEDED, host=spec.host, session_id_env=spec.session_id_env)
        # The one event that cannot wait for a later flush: `UNINSTALL.md` Part 3
        # may remove the very binary that would deliver it. A whole flush, not the
        # single-event `deliver=True` path — what this needs is the spool *emptied*
        # before the binary goes, not one envelope sent.
        events.flush()
        print(outcome)
        return 0

    if args.what == "error":
        events.record_agent_error(
            stage=args.stage,
            detail=args.detail,
            host=spec.host,
            session_id_env=spec.session_id_env,
        )
        # Delivered inline, for the same reason `docs install` flushes: the runs
        # that file an error are disproportionately the runs that never reach
        # `prepare` or `commit` — a failed install, a store the bridging pair
        # cannot talk to — so a later flush is exactly what cannot be counted on
        # here. An agent already blocked long enough to decide it had a failure to
        # report; one POST on that path is affordable, and fail-open means a
        # dead network costs the wait, not the event, which stays spooled.
        events.flush()
        print(outcome)
        return 0

    accepted, rejected = events.flush()
    print(f"delivered {accepted} event(s)")
    if rejected:
        # Never folded into the delivered count: a backend rejecting everything
        # must not read as healthy delivery.
        print(f"{rejected} event(s) discarded — the server rejected them", file=sys.stderr)
    return 0


def _register_report(sub: Any, handler: Any) -> None:
    parser = sub.add_parser("report", help="Report a lifecycle event to memU")
    what = parser.add_subparsers(dest="what", required=True)

    installed = what.add_parser("install", help="Record that installation completed successfully")
    installed.set_defaults(handler=handler)

    uninstalled = what.add_parser("uninstall", help="Record that memU was uninstalled (delivers immediately)")
    uninstalled.set_defaults(handler=handler)

    failed = what.add_parser("error", help="Report a failure memU could not observe on its own")
    failed.add_argument(
        "--stage",
        required=True,
        choices=events.STAGES,
        help="Which operation failed. 'other' is the catchall — use it rather than not reporting",
    )
    failed.add_argument(
        "--detail",
        default="",
        help=(
            "What went wrong, in your own words and in detail — a human reads this to work out "
            "what is broken on the machine, so say what you ran, what happened instead, and what "
            "you think the cause is. Not a traceback: memU already reports the exception itself. "
            "Never credentials, absolute paths, memory content, or transcript text. Truncated at "
            f"{events.MAX_DETAIL_CHARS} characters"
        ),
    )
    failed.set_defaults(handler=handler)

    flusher = what.add_parser("flush", help="Deliver any events still spooled on this machine")
    flusher.set_defaults(handler=handler)


def build_parser(spec: HostSpec) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=spec.binary,
        description=f"memU's {spec.display} host adapter — the scheduled bridging task and its install guide.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def with_base(p: argparse.ArgumentParser) -> argparse.ArgumentParser:
        p.add_argument(
            "--base-dir",
            default=spec.default_base_dir,
            help=f"memU working directory (default: {spec.default_base_dir})",
        )
        return p

    def bind(handler: Callable[[HostSpec, argparse.Namespace], Coroutine[Any, Any, int]]) -> Any:
        async def bound(args: argparse.Namespace) -> int:
            return await handler(spec, args)

        return bound

    # Both halves of the inject seam: what the agent runs, and what tells it to.
    # Shared across hosts, so they are registered, not redefined — only the file
    # the instruction lands in and the binary it names are ours to fill in.
    retrieval.register(sub, host=spec.host, session_id_env=spec.session_id_env)
    _register_report(sub, bind(_cmd_report))
    instruction.register(
        sub,
        path=spec.instruction_path,
        binary=spec.binary,
        skills_dir=spec.skills_dir,
        legacy_paths=spec.legacy_instruction_paths,
    )

    p = with_base(sub.add_parser("prepare", help=f"Slice new {spec.display} sessions into self-evolve job files"))
    # A host with no universal session location (the generic adapter) leaves
    # session_dir empty, which makes the flag mandatory instead of defaulted.
    p.add_argument(
        "--session-dir",
        default=spec.session_dir or None,
        required=not spec.session_dir,
        help=f"{spec.session_help}" + (f" (default: {spec.session_dir})" if spec.session_dir else ""),
    )
    p.add_argument("--max-jobs", type=int, default=MAX_JOBS, help=f"Sessions per run (default: {MAX_JOBS})")
    p.set_defaults(handler=bind(_cmd_prepare))

    p = with_base(sub.add_parser("commit", help="Submit what the self-evolve jobs produced back into memU"))
    p.set_defaults(handler=bind(_cmd_commit))

    p = with_base(
        sub.add_parser("verify-resources", help="Filter the touched-file log into the describe-me resource file")
    )
    p.set_defaults(handler=bind(_cmd_verify_resources))

    p = sub.add_parser("doctor", help="Verify MEMU_* config resolves and the selected memory backend is reachable")
    p.set_defaults(handler=bind(_cmd_doctor))

    p = sub.add_parser("docs", help="Print a packaged agent-facing guide")
    p.add_argument(
        "doc",
        choices=sorted(DOCS),
        help="install: the setup guide; task: the bridging-task procedure; uninstall: the removal guide",
    )
    p.set_defaults(handler=bind(_cmd_docs))

    # Windows-only automation of the bridging task's registration. The invocation
    # template, not the informational scheduler label, is the capability gate: hosts
    # without a Windows wrapper never advertise a `schedule` verb they cannot honour.
    if spec.schedule_command:
        p = with_base(
            sub.add_parser("schedule", help=f"Register the {spec.display} bridging task (Windows Task Scheduler)")
        )
        p.add_argument(
            "action",
            choices=("install", "uninstall", "status", "verify"),
            help="install/uninstall the task, show its status, or verify it can run",
        )
        p.add_argument("--interval", type=int, default=60, help="Minutes between runs, for install (default: 60)")
        p.set_defaults(handler=bind(_cmd_schedule))

    if spec.register_extra is not None:
        spec.register_extra(sub)

    return parser


def run(spec: HostSpec, argv: list[str] | None = None) -> int:
    # Piped stdio on Windows falls back to the ANSI code page (gbk, cp1252, …),
    # which cannot encode the guides' ✅ or stored memory content — and agents
    # read every command through a pipe. Force UTF-8; on UTF-8 stdio it's a no-op.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    args = build_parser(spec).parse_args(argv)
    handler: Callable[[argparse.Namespace], Coroutine[Any, Any, int]] = args.handler
    try:
        return asyncio.run(handler(args))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        # Where genuine unhandled failures already land, so it is free to observe
        # them here — and no model is in the loop, which makes this the
        # higher-quality of the two error feeds (ADR 0016 §5). Recorded with the
        # exception *type* and reduced frames only; the message is omitted,
        # because messages are where DSNs, tokens, and home paths surface.
        command = getattr(args, "command", "")
        events.record_cli_error(
            exc,
            command=command,
            host=spec.host,
            session_id_env=spec.session_id_env,
        )
        # Flushed here, unlike other errors: if what broke *is* prepare or commit,
        # the normal flush points are exactly the ones that will never run again.
        #
        # Never for `retrieve`, though, and the exception is the whole point. That
        # is the per-turn hook, and a store it cannot reach fails it on *every*
        # turn — so flushing here would put a blocking POST on the hot path, once
        # per turn, exactly when the user is already broken. Its events wait for
        # the bridging pair like any other.
        if command != "retrieve":
            events.flush()
        if os.environ.get("MEMU_DEBUG") == "1":
            raise
        print(f"error: {exc} (set MEMU_DEBUG=1 for a traceback)", file=sys.stderr)
        return 1
