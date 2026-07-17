"""``memu-agent`` — the generic host adapter, for every agent without its own.

Where the dedicated binaries hard-code one host's paths, this one starts with a
question: ``memu-agent detect`` probes the machine (or one agent's directory)
and reports, per agent, whether **memorization** works (a session log exists and
its records sniff as a known JSONL dialect) and whether **retrieval** works (an
instruction file like AGENTS.md / CLAUDE.md / SOUL.md exists for
``install-instruction --path`` to patch). The remaining verbs are the shared
host-adapter surface, pointed at whatever detect found.

Usage:
    memu-agent detect                       # survey ~ for agents; report both seams
    memu-agent detect ~/.someagent          # probe one agent's directory
    memu-agent retrieve "<query>"           # the inject seam — what the agent runs each turn
    memu-agent install-instruction --path F # patch the instruction file detect found
    memu-agent prepare --session-dir DIR    # slice new sessions into job files
    memu-agent verify-resources             # filter the touched-file log (run by a job)
    memu-agent commit                       # submit what the agent produced back to memU
    memu-agent doctor                       # check config + store before relying on them
    memu-agent docs install                 # print the agent-facing install guide
    memu-agent docs uninstall               # print the agent-facing removal guide
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from memu.hosts.generic.detect import probe, render, scan_home
from memu.hosts.generic.sessions import GenericTranscriptSource
from memu.hosts.host_cli import HostSpec, run

HOST = "agent"

AGENTS_MD = "./AGENTS.md"
"""The fallback inject target: most agents read the project root's AGENTS.md.
``detect`` reports the agent's real global file when it finds one — pass it
via ``--path``."""


async def _cmd_detect(args: argparse.Namespace) -> int:
    if args.path:
        print(render(probe(args.path)))
        return 0

    results = scan_home()
    if not results:
        print("no agent installations found under ~")
        return 0
    print("\n\n".join(render(result) for result in results))
    print(
        "\nnext steps: for a dedicated adapter, run its install guide; otherwise\n"
        "  memorization → memu-agent prepare --session-dir <dir>   (schedule via `memu-agent docs task`)\n"
        "  retrieval    → memu-agent install-instruction --path <file>"
    )
    return 0


def _register_detect(sub: Any) -> None:
    parser = sub.add_parser(
        "detect",
        help="Probe for agents: does memorization (session log) work, does retrieval (instruction file)?",
    )
    parser.add_argument("path", nargs="?", help="Agent directory to probe (default: survey all of ~)")
    parser.set_defaults(handler=_cmd_detect)


SPEC = HostSpec(
    host=HOST,
    display="agent",
    package="memu.hosts.generic",
    source_factory=GenericTranscriptSource,
    session_dir="",  # no universal location — detect finds it, prepare requires it
    session_help="The agent's session-log directory (find it with `memu-agent detect`)",
    instruction_path=AGENTS_MD,
    register_extra=_register_detect,
)


def main(argv: list[str] | None = None) -> int:
    return run(SPEC, argv)


if __name__ == "__main__":
    sys.exit(main())
