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
import os
import sys
import urllib.request
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from importlib.resources import files
from typing import Any

from memu.hosts import instruction, retrieval
from memu.hosts.base import TranscriptSource
from memu.hosts.bridging import Layout, commit, prepare
from memu.hosts.bridging.pipeline import MAX_JOBS
from memu.hosts.bridging.resources import verify_resource_log

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

    skills_dir: str = ""
    """The host's skills directory, for hosts that have skills (``~/.codex/skills``,
    ``~/.claude/skills``). Given one, ``install-instruction`` puts the retrieval
    procedure in a skill there and leaves only a pointer in ``instruction_path``.
    Empty — the default, and every host without a skills mechanism — keeps the full
    text inline, which is the only place it can live."""

    base_dir: str = ""
    """memU working tree. Empty means the per-host default ``~/.memu/hosts/<host>``;
    Codex overrides this with the pre-multi-host ``~/.memu`` it has always used."""

    extra_flags: dict[str, str] = field(default_factory=dict)
    """Reserved for host-specific flags; unused today."""

    register_extra: Callable[[Any], None] | None = None
    """Optional hook adding host-specific subcommands (the generic adapter's
    ``detect``). Called with the subparsers object after the shared verbs."""

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


def _layout(spec: HostSpec, args: argparse.Namespace) -> Layout:
    return Layout.default(host=spec.host, base=args.base_dir)


async def _cmd_prepare(spec: HostSpec, args: argparse.Namespace) -> int:
    source = spec.source_factory(args.session_dir)
    if not source.exists():
        print(f"error: no {spec.display} session log at {source.root()}", file=sys.stderr)
        return 2

    layout = _layout(spec, args)
    num_sessions = await prepare(source, layout, verify_command=spec.verify_command, max_jobs=args.max_jobs)
    num_jobs = 2 * num_sessions + 1
    print(f"prepared {num_sessions} session(s) -> {num_jobs} job(s) in {layout.jobs}")
    if num_sessions == 0:
        print("no new session turns since the last run; nothing to mine")
    return 0


async def _cmd_commit(spec: HostSpec, args: argparse.Namespace) -> int:
    result = await commit(_layout(spec, args))
    recall_files = result.get("recall_files", [])
    resources = result.get("resources", [])
    if not recall_files and not resources:
        print("nothing to commit")
        return 0
    print(f"committed {len(recall_files)} recall file(s) and {len(resources)} resource(s)")
    for recall_file in recall_files:
        print(f"  - {recall_file.get('track')}/{recall_file.get('name')}")
    return 0


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
    print((files(spec.package) / DOCS[args.doc]).read_text(encoding="utf-8"))
    return 0


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
    retrieval.register(sub)
    instruction.register(sub, path=spec.instruction_path, binary=spec.binary, skills_dir=spec.skills_dir)

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
        if os.environ.get("MEMU_DEBUG") == "1":
            raise
        print(f"error: {exc} (set MEMU_DEBUG=1 for a traceback)", file=sys.stderr)
        return 1
