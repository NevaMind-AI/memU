"""``init`` and ``config`` — the commands that write ``config.env`` (ADR 0017).

Two verbs over one writer, because they have different *policies* and are named
on surfaces with different update rates. ``init`` is the inferring front door,
named in ``SKILL.md`` — the least updatable surface memU has, so its contract is
one optional flag and is expected to hold for years. ``config`` is the explicit
one, driven by ``INSTALL.md``, which *is* server-refreshable (ADR 0013) and can
therefore grow flags at the server's pace.

What they share is :mod:`memu.config_file`: neither owns a code path for
``MEMU_CLOUD_API_KEY``, or the two drift within a release.

**Every guard here reads the file, never :func:`memu.env.env`.** The question is
"does this machine have memory to lose", and only the file can answer it — an
exported ``MEMU_CLOUD_API_KEY`` in the calling shell would otherwise make
``config --local`` refuse a file that declares nothing at all.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from typing import Any

from memu import config_file, events
from memu import env as env_module

IDENTITY_KEYS = ("MEMU_DB", "MEMU_EMBED_PROVIDER", "MEMU_EMBED_MODEL")
"""Keys that bind an embedding space, and may never be *changed* without ``--force``.

Unlike the mode, these get no state test. The three together decide which vectors
a query can be compared against, so "fixing" one on a store that already has
vectors strands every one of them — silently, because retrieval still succeeds and
simply finds nothing. Setting one that is absent is not a change and is free;
``--force`` is the escape for the genuine repair, and exists so the alternative
(the user hand-editing the file) does not become the only route.
"""

REFUSED = 2
"""Exit status for a guard refusal.

Matches ``prepare``'s missing-session-log, and it is *returned*, never raised:
:func:`memu.hosts.host_cli.run` turns an exception into a ``cli_error`` event and
flushes it, which would file every ordinary "you meant ``--force``" into the feed
that exists to show memU breaking.
"""


def _row(label: str, value: str) -> None:
    """One aligned output line, in ``doctor``'s shape."""
    print(f"{label:<10}{value}")


def _declared_mode(values: dict[str, str]) -> str:
    """The mode the file states, or ``""`` if it states none (or nonsense)."""
    raw = values.get("MEMU_MEMORY_MODE", "").strip().lower()
    return raw if raw in ("local", "cloud") else ""


def _effective_mode(values: dict[str, str]) -> str:
    """The mode this file actually resolves to, absent declaration included.

    Not the same question as :func:`_declared_mode`, and the difference is what
    keeps a legacy install safe. A ``config.env`` written before ``MEMU_MEMORY_MODE``
    existed declares no mode but is *in* local mode — :func:`memu.env.memory_mode`
    defaults there for exactly that compatibility. Reading it as "vacuous" would
    make ``config --cloud`` a silent, unguarded flip on the one population most
    likely to have a large local store.
    """
    return _declared_mode(values) or "local"


def _protection(values: dict[str, str]) -> str | None:
    """What the current backend has to lose, or ``None`` if it is vacuous.

    The state test ADR 0017 turns on: an *inferred* default is indistinguishable
    from a *chosen* one once written, so a guard that reads the declaration alone
    refuses the most ordinary first install (bare ``init`` lands ``local``, the
    guide then asks the question, the user says cloud). What the invariant
    protects is existing memory, so that is what gets asked about.

    One question, two policies. ``config`` refuses on it, because its caller asked
    for a specific backend and can be handed ``--force``; ``init`` only warns, and
    the difference is that ``init`` has no override to hand back.

    Declaration of a store, not its contents: ``MEMU_DB`` spans a bare path, a
    ``sqlite://`` URL, a ``postgres://`` DSN and an in-memory sentinel, so "does
    the store exist" has no single cheap meaning — and in the one shape where it
    is cheap, :func:`memu.env.database_config` answers it by *creating the parent
    directory*. A guard that mutates the filesystem to decide is worse than one
    that over-refuses, and over-refusing costs one ``--force``.
    """
    if _effective_mode(values) == "cloud":
        if values.get("MEMU_CLOUD_API_KEY"):
            return "a memU Cloud key is already stored"
        return None
    if values.get("MEMU_DB"):
        return "a local store is already configured (MEMU_DB)"
    return None


def _client_id(values: dict[str, str]) -> tuple[dict[str, str], str, bool]:
    """``MEMU_CLIENT_ID``, generated into the update set if the file lacks one.

    Persisted here rather than being left to whichever event fires first, so the
    id exists before anything reports (ADR 0016 §4). Read from the file, not
    :func:`memu.events.client_instance_id`, for the module-wide reason: this is a
    statement about the file's contents.
    """
    existing = values.get("MEMU_CLIENT_ID", "")
    if existing:
        return {}, existing, False
    generated = str(uuid.uuid4())
    return {"MEMU_CLIENT_ID": generated}, generated, True


def _short(client_id: str) -> str:
    return f"{client_id[:4]}…" if len(client_id) > 4 else client_id


def _write(updates: dict[str, str]) -> None:
    """Persist, re-resolve so anything later in this process sees it, and report.

    The report is a decisive summary, not a diff, and it comes *after* the caller's
    own rows: what the agent needs first is what this machine's backend now is, and
    where the file lives only matters once it is asking a different question.
    """
    path, _ = config_file.write_values(updates)
    env_module.reload()
    _row("config", f"{path} ({config_file.permission_note()})")


def _report_install_started(args: argparse.Namespace) -> None:
    """The install funnel's start (ADR 0016 §4, ADR 0017), recorded by ``init``.

    ``SKILL.md`` Step 2 is the first command on the install path, so it is the
    earliest point that proves ``memu-cli`` is installed and resolving — earlier
    than ``docs install``, which now reports the narrower
    :data:`memu.events.INSTALL_GUIDE_OPENED`.

    **Called after :func:`_write`, never before**, and that is the whole reason
    this is a function rather than a line at the top of ``init``. The id every
    envelope carries comes from :func:`memu.events.client_instance_id`, which
    reads ``MEMU_CLIENT_ID`` from the resolved environment — where the one
    :func:`_client_id` just generated does not appear until ``_write`` has
    persisted it and reloaded. Report first and the event generates and persists a
    *second* id, which ``_write`` then overwrites: one machine reporting under two
    identities, and the ``client`` row printed above naming neither. The same
    ordering is what puts a ``--cloud-api-key`` into :func:`memu.events._headers`,
    so the first event of an install is attributable rather than anonymous.

    Nothing between :func:`_client_id` and here does I/O or can raise, so the
    alternative — an extra ``_write`` early to bank the id against a later error —
    buys no durability, costs a second read-modify-write, and prints the ``config``
    row twice.

    Flushed rather than left spooled, for the reason ``docs install`` flushes: an
    install that stops before the bridging pair ever runs has no other flush point,
    and that run is exactly the one the funnel exists to show. Both calls are
    fail-open, so an unreachable endpoint costs this command its timeout and
    nothing else — never its exit code, and never the file it just wrote.
    """
    events.record(
        events.CLI_INSTALL_STARTED,
        host=getattr(args, "host", ""),
        session_id_env=getattr(args, "session_id_env", ""),
    )
    events.flush()


async def _cmd_init(args: argparse.Namespace) -> int:
    """Infer the backend from what the caller had to offer, and never lose a mode.

    The one command ``SKILL.md`` names, so it must be safe to run on any machine
    in any state — including one another host already configured. It never
    refuses: it is the first step of the install, and a non-zero exit here with no
    ``--force`` to offer strands every step after it.
    """
    values = config_file.read()
    declared = _declared_mode(values)
    updates, client_id, generated = _client_id(values)

    if not args.cloud_api_key:
        # Nothing offered, so nothing is inferred: an existing mode is kept, and
        # only a file that states none gets `local` — which is the mode it already
        # resolves to, written down. A re-install where the user did not re-supply
        # a key must never demote cloud to local.
        if not declared:
            updates["MEMU_MEMORY_MODE"] = "local"
        if declared:
            _row("mode", f"{declared} (kept)")
        elif values.get("MEMU_DB"):
            _row("mode", "local (recorded; the existing store is unchanged)")
        else:
            _row("mode", "local (default; no store configured yet)")
        _row("client", f"{_short(client_id)}{' (generated)' if generated else ''}")
        _write(updates)
        _report_install_started(args)
        print(f"ready — continue with `{args.binary} docs install`")
        return 0

    # A key *is* the choice of cloud, and `init` acts on it even over a configured
    # local store. `config`'s state guard (:func:`_refuse_flip`) is deliberately not
    # applied here: `init` has no `--force`, so a refusal is terminal, and it is the
    # first command on the install path — halting there halts everything after it.
    # Having a key to hand is a strong enough statement of intent to honour, and
    # nothing is destroyed by honouring it; the local store stays on disk, merely
    # unread until the mode is switched back. So the cost is a warning, not a veto.
    orphaned = _protection(values) if _effective_mode(values) != "cloud" else None

    stored = values.get("MEMU_CLOUD_API_KEY", "")
    replacing = bool(stored) and stored != args.cloud_api_key
    updates["MEMU_MEMORY_MODE"] = "cloud"
    updates["MEMU_CLOUD_API_KEY"] = args.cloud_api_key
    _row("mode", "cloud (from --cloud-api-key)")
    if orphaned:
        # Named on stdout beside the mode, because an agent that reads only the
        # rows must still see that this run changed the backend out from under a
        # store, and told in full below, because the user may not have meant it.
        _row("switched", f"{orphaned} and is no longer read")
    # Loud, because the client cannot tell a rotated key from a different account.
    # Refusing would block the legitimate repair; saying nothing would hide the
    # case where it was not one.
    _row("key", "replaced — the previously stored memU Cloud key is gone" if replacing else "set")
    _row("client", f"{_short(client_id)}{' (generated)' if generated else ''}")
    _write(updates)
    if orphaned:
        # The only place this module writes to both streams in one run, so the only
        # place ordering has to be forced: piped stdout is block-buffered and would
        # otherwise flush *after* the warning, putting it above the block it follows.
        sys.stdout.flush()
        print(
            "warning: this machine was in local mode with a store configured. Nothing was "
            "deleted, but memories written there are not visible to cloud memory, and new "
            "ones now go to the cloud account this key belongs to.",
            file=sys.stderr,
        )
        print(f"To go back: `{args.binary} config --local --force`", file=sys.stderr)
    # Below the warning rather than beside the write, unlike the branch above:
    # this one blocks on a POST, and the warning is the line a user has to read.
    _report_install_started(args)
    print(f"ready — continue with `{args.binary} docs install`")
    return 0


def _refuse_flip(values: dict[str, str], target: str, binary: str) -> int | None:
    if _effective_mode(values) == target:
        return None
    why = _protection(values)
    if why is None:
        return None
    print(
        f"error: {why}, so switching this machine to {target} memory is refused. Record and "
        "retrieval must agree on one backend, or retrieval silently finds nothing.",
        file=sys.stderr,
    )
    print(
        f"If you mean to switch anyway, re-run with --force (`{binary} config --{target} … --force`).", file=sys.stderr
    )
    return REFUSED


def _refuse_identity(values: dict[str, str], updates: dict[str, str]) -> int | None:
    for key in IDENTITY_KEYS:
        new = updates.get(key)
        old = values.get(key, "")
        if new is None or not old or new == old:
            continue
        print(
            f"error: {key} is already set on this machine, and changing it strands every vector "
            "already written against it — retrieval keeps succeeding and finds nothing.",
            file=sys.stderr,
        )
        print(
            "Repair the connection, never the identity. Re-run with --force only if the store is "
            "genuinely being replaced.",
            file=sys.stderr,
        )
        return REFUSED
    return None


async def _cmd_config(args: argparse.Namespace) -> int:
    """Set the backend explicitly. The verb ``INSTALL.md`` drives."""
    if args.show:
        return _show()
    if not args.cloud and not args.local:
        # Mandatory, and not enforced by argparse's `required=True` only because
        # `show` shares this parser. The refusal is the point of the verb: this is
        # the explicit one, and a `config` that guessed a backend would be `init`.
        print("error: `config` needs --cloud or --local.", file=sys.stderr)
        print(f"To read the configuration without writing anything: `{args.binary} config show`", file=sys.stderr)
        return REFUSED

    values = config_file.read()
    target = "cloud" if args.cloud else "local"
    if not args.force:
        refused = _refuse_flip(values, target, args.binary)
        if refused is not None:
            return refused

    updates = _updates_for(target, args)
    if not args.force:
        refused = _refuse_identity(values, updates)
        if refused is not None:
            return refused

    updates.update(_client_id(values)[0])
    _row("mode", target + (" (forced)" if args.force else ""))
    _report_backend(target, values, updates)
    _write(updates)
    print(f"ready — verify with `{args.binary} doctor`")
    return 0


def _updates_for(target: str, args: argparse.Namespace) -> dict[str, str]:
    """The keys this invocation sets — the mode, plus whichever flags were passed."""
    updates: dict[str, str] = {"MEMU_MEMORY_MODE": target}
    if target == "cloud":
        _collect(updates, args, (("cloud_api_key", "MEMU_CLOUD_API_KEY"),))
        # Never persisted when it equals today's default: baking that value into
        # the file freezes across upgrades a URL the code should own.
        from memu.cloud import DEFAULT_CLOUD_BASE_URL

        if args.cloud_base_url and args.cloud_base_url != DEFAULT_CLOUD_BASE_URL:
            updates["MEMU_CLOUD_BASE_URL"] = args.cloud_base_url
        return updates

    _collect(
        updates,
        args,
        (
            ("db", "MEMU_DB"),
            ("embed_provider", "MEMU_EMBED_PROVIDER"),
            ("embed_model", "MEMU_EMBED_MODEL"),
            # The embedding provider's credential and endpoint — never memU
            # Cloud's. The two are one careless `--api-key` away from being
            # confused, which is why neither flag is called that.
            ("embed_api_key", "MEMU_API_KEY"),
            ("embed_base_url", "MEMU_BASE_URL"),
        ),
    )
    return updates


def _report_backend(target: str, values: dict[str, str], updates: dict[str, str]) -> None:
    """The one line that says whether this backend can actually work."""
    if target == "local":
        _row("store", updates.get("MEMU_DB") or values.get("MEMU_DB") or "unset — set one with --db before `doctor`")
        return
    stored, new = values.get("MEMU_CLOUD_API_KEY", ""), updates.get("MEMU_CLOUD_API_KEY", "")
    if new and stored and new != stored:
        _row("key", "replaced — the previously stored memU Cloud key is gone")
    elif new or stored:
        _row("key", "set")
    else:
        # Said now rather than left to the gate: cloud mode without a key is not a
        # partial configuration, it is one that cannot work.
        _row("key", "unset — cloud memory needs one; `doctor` will fail until it is set")


def _collect(updates: dict[str, str], args: argparse.Namespace, pairs: tuple[tuple[str, str], ...]) -> None:
    """Copy the flags the caller actually passed into the update set.

    Absent flags are absent from the write, which is what makes every one of these
    commands a merge rather than a form submission: `config --local --db X` on a
    configured machine changes the store and leaves the provider alone.
    """
    for attr, key in pairs:
        value = getattr(args, attr, None)
        if value:
            updates[key] = value


def _show() -> int:
    """Print what the file declares. Writes nothing — the whole point.

    Named ``show`` rather than being what a bare ``config`` does. A bare verb that
    printed while a bare ``init`` wrote is exactly the asymmetry agents get wrong,
    and this one is quoted in guides that an agent runs before deciding whether to
    configure anything.
    """
    path = config_file.config_path()
    values = config_file.read()
    if not path.is_file():
        _row("config", f"{path} (not created yet)")
        _row("mode", "local (default; nothing configured)")
        return 0

    _row("config", str(path))
    declared = _declared_mode(values)
    _row("mode", declared or "local (undeclared; local for backward compatibility)")
    if _effective_mode(values) == "cloud":
        _row("key", "set" if values.get("MEMU_CLOUD_API_KEY") else "unset")
        _row("endpoint", values.get("MEMU_CLOUD_BASE_URL") or "default")
    else:
        _row("store", values.get("MEMU_DB") or "unset")
        _row("provider", values.get("MEMU_EMBED_PROVIDER") or values.get("MEMU_LLM_PROVIDER") or "openai (default)")
        _row("model", values.get("MEMU_EMBED_MODEL") or "provider default")
        _row("embed key", "set" if values.get("MEMU_API_KEY") else "unset")
    _row("client", _short(values.get("MEMU_CLIENT_ID", "")) or "unset")

    # This command reports the *file*, but the process environment is what would
    # actually win at runtime (`env.env`). Where the two disagree, saying so is
    # the difference between a probe and a misleading one.
    shadowed = sorted(
        key
        for key in ("MEMU_MEMORY_MODE", "MEMU_DB", "MEMU_CLOUD_API_KEY", "MEMU_EMBED_PROVIDER", "MEMU_EMBED_MODEL")
        if os.environ.get(key) and os.environ[key] != values.get(key)
    )
    if shadowed:
        print(f"note: the environment overrides what this file says for {', '.join(shadowed)}")
    return 0


def register(sub: Any, *, binary: str, host: str = "", session_id_env: str = "") -> None:
    """Add ``init`` and ``config`` to a host CLI's subparsers.

    ``binary`` is the host adapter's own command name, carried on the parser
    defaults purely so the next-step lines name the binary the agent is already
    holding — ``SKILL.md``'s ergonomic bet is that one binary name serves the
    whole flow.

    ``host`` and ``session_id_env`` ride the same way, and only ``init`` reads
    them: they are the envelope context for the install-start event
    (:func:`_report_install_started`), which is the one thing in this module that
    is not host-irrelevant. Both default to empty, so a caller that has no host —
    the core ``memu`` binary, were these ever registered there — gets commands
    that work and an event that reports ``agent_platform: none``.
    """
    initialiser = sub.add_parser(
        "init",
        help="Create or update ~/.memu/config.env — the one command SKILL.md names before `docs install`",
    )
    initialiser.add_argument(
        "--cloud-api-key",
        default="",
        help="The user's memU Cloud key. Providing one selects cloud memory; omit it to keep or default the mode",
    )
    initialiser.set_defaults(handler=_cmd_init, binary=binary, host=host, session_id_env=session_id_env)

    configure = sub.add_parser(
        "config",
        help="Set the memory backend explicitly in ~/.memu/config.env, or `config show` to read it",
    )
    # `show` as a positional rather than a flag, so the read side is a name an
    # agent types deliberately and can never be a bare `config` that wrote.
    configure.add_argument(
        "show",
        nargs="?",
        choices=("show",),
        help="Print the declared configuration and exit, writing nothing",
    )
    mode = configure.add_mutually_exclusive_group()
    mode.add_argument("--cloud", action="store_true", help="Select memU Cloud memory")
    mode.add_argument("--local", action="store_true", help="Select local memory on this device")
    configure.add_argument("--cloud-api-key", default="", help="memU Cloud key (cloud mode)")
    configure.add_argument("--cloud-base-url", default="", help="Override the memU Cloud endpoint (cloud mode)")
    configure.add_argument("--db", default="", help="Local store: an absolute path, a sqlite:// or a postgres:// DSN")
    configure.add_argument("--embed-provider", default="", help="Embedding provider id (openai, jina, voyage, …)")
    configure.add_argument("--embed-model", default="", help="Embedding model id")
    # Named for the variable it writes, never `--api-key`: MEMU_API_KEY is the
    # embedding provider's credential and MEMU_CLOUD_API_KEY is memU Cloud's, and
    # this is the one surface meant to close the door on confusing them.
    configure.add_argument("--embed-api-key", default="", help="Embedding provider credential (MEMU_API_KEY)")
    configure.add_argument(
        "--embed-base-url", default="", help="Embedding endpoint, e.g. a local OpenAI-compatible server"
    )
    configure.add_argument(
        "--force",
        action="store_true",
        help="Override the one-backend guard. Only when the store is genuinely being replaced",
    )
    configure.set_defaults(handler=_cmd_config, binary=binary)
