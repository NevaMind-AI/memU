"""The inject seam's other half — the standing instruction, shared by every host.

:mod:`memu.hosts.retrieval` is what *runs* when the agent retrieves. This is what
makes it run: one paragraph, patched into the host's global instruction file
(Codex's ``~/.codex/AGENTS.md``, and whatever the next host calls its own), which
that host loads into every session. No hook, no wrapper, no per-turn process.

It lives here for the same reason retrieval does (ADR 0008): the text does not
differ per host — only the file it lands in does. So the string is owned once,
and each host CLI registers the command against its own path.

Owning it in code rather than in the install guide is deliberate. A payload
transcribed out of a Markdown fence by an agent is a payload that gets
paraphrased, and one pasted into a user's file is one that can never be upgraded:
when :data:`INSTRUCTION` improves in a later release, the copy already sitting in
someone's AGENTS.md is inert. Hence :func:`install` writes a *managed block*
between markers — re-running replaces it in place, so an upgrade is a re-run.
Everything outside the markers is the user's and is never touched.
"""

from __future__ import annotations

import argparse
import difflib
import re
import shutil
from pathlib import Path
from typing import Any

BEGIN = "<!-- memu:begin — managed block, do not edit (memu-codex install-instruction) -->"
END = "<!-- memu:end -->"

INSTRUCTION = """\
## memU — retrieve before answering

Before answering, run `memu-codex retrieve "<query>"` — where <query> is the
user's request, reworded into a clearer query or focused keywords when that
retrieves better (you need not pass their raw words verbatim). Use any relevant
results as context. If it returns nothing, proceed normally.

The result unfolds progressively, in three layers. `segments` are the narrowest
and usually the most on-point: the individual slices of memory that matched the
query. `files` are the synthesized documents those segments were cut from —
broader, and worth consulting when a segment reads as relevant but is too thin to
act on. `resources` are files on the user's own machine that look related. Files
and resources come back as a location plus a summary rather than full text; work
from the summary, and open the raw file only when you need what it leaves out.
"""
"""What the agent is told, every turn, before it answers.

It names ``memu-codex retrieve`` — a ``PATH`` command, never a script path, and
the LLM-free single-shot retrieval. It fails open, hence "proceed normally" — an
empty store returns empty lists and the turn goes on.

The second paragraph is a legend for the JSON. ``retrieve`` prints raw
``segments``/``files``/``resources`` with nothing to explain them, and the layers
are not interchangeable: a segment is a matched slice, a file is the synthesized
document that slice came from, a resource is a file on disk. Without the legend
the reader has to guess which layer to trust, and opens raw files it did not need.
"""

_BLOCK = re.compile(
    rf"^{re.escape(BEGIN)}\n.*?^{re.escape(END)}\n?",
    re.DOTALL | re.MULTILINE,
)


def block() -> str:
    """The managed block exactly as it is written to disk, markers included."""
    return f"{BEGIN}\n{INSTRUCTION}{END}\n"


def patch(current: str) -> str:
    """Return ``current`` with the managed block installed — replaced, or appended.

    Pure, so the interesting half of :func:`install` is testable without a
    filesystem. Idempotent by construction: the markers delimit what memU owns, so
    a second call replaces the first call's block rather than stacking another
    copy, and text outside them survives untouched.
    """
    if _BLOCK.search(current):
        return _BLOCK.sub(lambda _: block(), current, count=1)
    if current and not current.endswith("\n"):
        current += "\n"
    separator = "\n" if current else ""
    return f"{current}{separator}{block()}"


def install(path: Path, *, dry_run: bool = False) -> tuple[bool, str]:
    """Install the managed block into ``path``. Returns ``(changed, diff)``.

    Creates the file (and its parent) if absent, and backs up any existing content
    to ``<path>.bak`` before rewriting it — the target belongs to the *host*, not
    to memU, and may hold instructions that have nothing to do with us.
    """
    path = path.expanduser()
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    updated = patch(current)
    diff = "".join(
        difflib.unified_diff(
            current.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
        )
    )
    if updated == current or dry_run:
        return False, diff

    path.parent.mkdir(parents=True, exist_ok=True)
    if current:
        shutil.copyfile(path, path.with_suffix(path.suffix + ".bak"))
    path.write_text(updated, encoding="utf-8")
    return True, diff


def _cmd_install_instruction(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if args.print_only:
        print(block(), end="")
        return 0

    changed, diff = install(path, dry_run=args.dry_run)
    if not diff:
        print(f"{path}: already up to date")
        return 0
    if args.dry_run:
        print(f"{path}: would change\n\n{diff}", end="")
        return 0
    print(f"{path}: {'updated' if changed else 'unchanged'}\n\n{diff}", end="")
    return 0


async def _cmd_install_instruction_async(args: argparse.Namespace) -> int:
    """The host CLIs dispatch coroutines; this command needs no I/O loop of its own."""
    return _cmd_install_instruction(args)


def register(sub: Any, *, path: str) -> None:
    """Add ``install-instruction`` to a host CLI, bound to that host's ``path``."""
    parser = sub.add_parser(
        "install-instruction",
        help="Patch the host's global instruction file so the agent retrieves before answering",
    )
    parser.add_argument("--path", default=path, help=f"Instruction file to patch (default: {path})")
    parser.add_argument("--dry-run", action="store_true", help="Show the diff without writing")
    parser.add_argument("--print", dest="print_only", action="store_true", help="Print the managed block and exit")
    parser.set_defaults(handler=_cmd_install_instruction_async)
