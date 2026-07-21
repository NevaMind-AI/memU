"""The inject seam's other half — the standing instruction, shared by every host.

:mod:`memu.hosts.retrieval` is what *runs* when the agent retrieves. This is what
makes it run: one paragraph, patched into the host's global instruction file
(Codex's ``~/.codex/AGENTS.md``, Claude Code's ``~/.claude/CLAUDE.md``, and
whatever the next host calls its own), which that host loads into every session.
No hook, no wrapper, no per-turn process.

It lives here for the same reason retrieval does (ADR 0008): the text does not
differ per host — only the file it lands in and the binary it names do. So the
string is owned once as a template, and each host CLI registers the command
against its own path and its own binary.

Owning it in code rather than in the install guide is deliberate. A payload
transcribed out of a Markdown fence by an agent is a payload that gets
paraphrased, and one pasted into a user's file is one that can never be upgraded:
when :data:`INSTRUCTION_TEMPLATE` improves in a later release, the copy already
sitting in someone's AGENTS.md is inert. Hence :func:`install` writes a *managed
block* between markers — re-running replaces it in place, so an upgrade is a
re-run. Everything outside the markers is the user's and is never touched.

Hosts that support **skills** take a second shape. The detail — how to word the
query, how to read the three result layers — is not needed until the agent is
actually retrieving, and an instruction file is read on every turn of every
session, whether or not memory is in play. So on those hosts the detail moves
into a skill (:data:`SKILL_TEMPLATE`, installed under the host's ``skills/``
directory) and what lands in the instruction file shrinks to
:data:`SKILL_INSTRUCTION_TEMPLATE`: two sentences pointing at it. Same seam, same
markers, same upgrade-by-re-run; only the split differs. A host with no skills
directory (:attr:`~memu.hosts.host_cli.HostSpec.skills_dir` left empty) gets the
full text inline and no skill folder, because for it there is nowhere to put one.
"""

from __future__ import annotations

import argparse
import difflib
import re
import shutil
from pathlib import Path
from typing import Any

BEGIN_TEMPLATE = "<!-- memu:begin — managed block, do not edit ({binary} install-instruction) -->"
END = "<!-- memu:end -->"

SKILL_NAME = "memu-retrieve"
"""Directory and frontmatter name of the installed skill — ``<skills>/memu-retrieve/SKILL.md``."""

RETRIEVAL_BODY = """\
Run `{binary} retrieve "<query>"` — where <query> is the user's request, reworded
into a clearer query or focused keywords when that retrieves better (you need not
pass their raw words verbatim). Use any relevant results as context. If it returns
nothing, proceed normally.

The result unfolds progressively, in three layers. `segments` are the narrowest
and usually the most on-point: the individual slices of memory that matched the
query. `files` are the synthesized documents those segments were cut from —
broader, and worth consulting when a segment reads as relevant but is too thin to
act on. `resources` are files on the user's own machine that look related. Files
and resources come back as a location plus a summary rather than full text; work
from the summary, and open the raw file only when you need what it leaves out.
"""

INSTRUCTION_TEMPLATE = f"""\
## memU — retrieve before answering

Before answering:

{RETRIEVAL_BODY}"""

SKILL_INSTRUCTION_TEMPLATE = """\
## memU — retrieve before answering

Before answering, use the `{skill}` skill to pull any relevant memory into
context. It fails open: if nothing comes back, answer normally.
"""

SKILL_TEMPLATE = f"""\
---
name: {SKILL_NAME}
description: Retrieve the user's durable memory from memU before answering — past
  decisions, preferences, projects, and related files on this machine. Use at the
  start of any turn where what the user has said or done before could matter.
---

# Retrieve from memU before answering

{RETRIEVAL_BODY}"""


def begin(binary: str) -> str:
    """The opening marker, naming the host binary that manages the block."""
    return BEGIN_TEMPLATE.format(binary=binary)


def skill_document(binary: str) -> str:
    """The ``SKILL.md`` as written to disk, telling the agent how to retrieve."""
    return SKILL_TEMPLATE.format(binary=binary)


def instruction(binary: str, *, skill: bool = False) -> str:
    """The instruction text, telling the agent to run this host's ``retrieve``.

    ``skill=True`` returns the short pointer for hosts where :func:`install_skill`
    has put the detail in a skill; otherwise the full inline text.
    """
    if skill:
        return SKILL_INSTRUCTION_TEMPLATE.format(skill=SKILL_NAME, binary=binary)
    return INSTRUCTION_TEMPLATE.format(binary=binary)


def block(binary: str, *, skill: bool = False) -> str:
    """The managed block exactly as it is written to disk, markers included."""
    return f"{begin(binary)}\n{instruction(binary, skill=skill)}{END}\n"


def _block_re(binary: str) -> re.Pattern[str]:
    return re.compile(
        rf"^{re.escape(begin(binary))}\n.*?^{re.escape(END)}\n?",
        re.DOTALL | re.MULTILINE,
    )


def patch(current: str, binary: str, *, skill: bool = False) -> str:
    """Return ``current`` with the managed block installed — replaced, or appended.

    Pure, so the interesting half of :func:`install` is testable without a
    filesystem. Idempotent by construction: the markers delimit what memU owns, so
    a second call replaces the first call's block rather than stacking another
    copy, and text outside them survives untouched.
    """
    pattern = _block_re(binary)
    if pattern.search(current):
        return pattern.sub(lambda _: block(binary, skill=skill), current, count=1)
    if current and not current.endswith("\n"):
        current += "\n"
    separator = "\n" if current else ""
    return f"{current}{separator}{block(binary, skill=skill)}"


def strip(current: str, binary: str) -> str:
    """Return ``current`` with the managed block removed — the inverse of :func:`patch`.

    Pure, for the same reason :func:`patch` is. Only the marker-fenced block is
    memU's to take back; everything outside it is the user's and survives
    verbatim. Removing the block also takes back the blank-line separator
    :func:`patch` added, so an install/remove round-trip restores the file
    byte-for-byte.
    """
    pattern = _block_re(binary)
    if not pattern.search(current):
        return current
    stripped = pattern.sub("", current, count=1)
    stripped = re.sub(r"\n{3,}", "\n\n", stripped)
    if not stripped.strip():
        return ""
    return stripped.rstrip("\n") + "\n"


def _write(path: Path, updated: str, *, backup: bool, dry_run: bool) -> tuple[bool, str]:
    """Rewrite ``path`` to ``updated``, diffing first. Returns ``(changed, diff)``."""
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
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
    if backup and current:
        shutil.copyfile(path, path.with_suffix(path.suffix + ".bak"))
    path.write_text(updated, encoding="utf-8")
    return True, diff


def install(path: Path, binary: str, *, skill: bool = False, dry_run: bool = False) -> tuple[bool, str]:
    """Install the managed block into ``path``. Returns ``(changed, diff)``.

    Creates the file (and its parent) if absent, and backs up any existing content
    to ``<path>.bak`` before rewriting it — the target belongs to the *host*, not
    to memU, and may hold instructions that have nothing to do with us.

    ``skill`` installs the short block that points at :func:`install_skill`'s skill
    instead of the full inline text; pass it only when that skill is being
    installed too, or the block points at nothing.
    """
    path = path.expanduser()
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    return _write(path, patch(current, binary, skill=skill), backup=True, dry_run=dry_run)


def remove(path: Path, binary: str, *, dry_run: bool = False) -> tuple[bool, str]:
    """Remove the managed block from ``path``. Returns ``(changed, diff)``.

    The uninstall-side mirror of :func:`install`, with the same safety
    properties: only the marked block goes, the user's content stays, and the
    previous contents are backed up to ``<path>.bak`` before the rewrite. A
    missing file — or one with no managed block — is already the desired end
    state, so both are clean no-ops rather than errors.
    """
    path = path.expanduser()
    if not path.is_file():
        return False, ""
    current = path.read_text(encoding="utf-8")
    return _write(path, strip(current, binary), backup=True, dry_run=dry_run)


def skill_path(skills_dir: Path) -> Path:
    """Where the skill lands inside a host's ``skills/`` directory."""
    return skills_dir.expanduser() / SKILL_NAME / "SKILL.md"


def install_skill(skills_dir: Path, binary: str, *, dry_run: bool = False) -> tuple[bool, str]:
    """Install the retrieval skill under ``skills_dir``. Returns ``(changed, diff)``.

    Unlike the instruction file, ``<skills_dir>/memu-retrieve/`` is memU's own —
    nothing of the user's lives there — so it is overwritten whole rather than
    marker-fenced and backed up. Same upgrade story either way: re-run and the
    release's text replaces the installed one.
    """
    return _write(skill_path(skills_dir), skill_document(binary), backup=False, dry_run=dry_run)


def _report(path: Path, changed: bool, diff: str, *, dry_run: bool) -> None:
    if not diff:
        print(f"{path}: already up to date")
    elif dry_run:
        print(f"{path}: would change\n\n{diff}", end="")
    else:
        print(f"{path}: {'updated' if changed else 'unchanged'}\n\n{diff}", end="")


def _cmd_install_instruction(args: argparse.Namespace) -> int:
    skills_dir = Path(args.skills_dir) if args.skills_dir else None
    skill = skills_dir is not None
    if args.print_only:
        if skills_dir is not None:
            print(f"# {skill_path(skills_dir)}\n\n{skill_document(args.binary)}")
        print(block(args.binary, skill=skill), end="")
        return 0

    # The skill goes in first: between the two writes, an instruction block naming
    # a skill that is not there yet is the only order that can mislead an agent.
    if skills_dir is not None:
        changed, diff = install_skill(skills_dir, args.binary, dry_run=args.dry_run)
        _report(skill_path(skills_dir), changed, diff, dry_run=args.dry_run)

    path = Path(args.path)
    changed, diff = install(path, args.binary, skill=skill, dry_run=args.dry_run)
    _report(path.expanduser(), changed, diff, dry_run=args.dry_run)
    return 0


def _cmd_remove_instruction(args: argparse.Namespace) -> int:
    path = Path(args.path)
    changed, diff = remove(path, args.binary, dry_run=args.dry_run)
    if not diff:
        print(f"{path}: no managed block to remove")
        return 0
    if args.dry_run:
        print(f"{path}: would change\n\n{diff}", end="")
        return 0
    print(f"{path}: {'updated' if changed else 'unchanged'}\n\n{diff}", end="")
    return 0


async def _cmd_install_instruction_async(args: argparse.Namespace) -> int:
    """The host CLIs dispatch coroutines; this command needs no I/O loop of its own."""
    return _cmd_install_instruction(args)


async def _cmd_remove_instruction_async(args: argparse.Namespace) -> int:
    """The host CLIs dispatch coroutines; this command needs no I/O loop of its own."""
    return _cmd_remove_instruction(args)


def register(sub: Any, *, path: str, binary: str, skills_dir: str = "") -> None:
    """Add ``install-instruction`` to a host CLI, bound to that host's ``path``.

    ``binary`` is the host adapter's own command name (``memu-codex``, …) — it is
    what the installed instruction tells the agent to run.

    ``skills_dir`` is the host's skills directory (``~/.claude/skills``, …), if it
    has one. Given it, the command installs the retrieval skill there and patches
    ``path`` with a two-sentence pointer to it; left empty, it patches ``path``
    with the full text and writes no skill.
    """
    parser = sub.add_parser(
        "install-instruction",
        help="Patch the host's global instruction file so the agent retrieves before answering",
    )
    parser.add_argument("--path", default=path, help=f"Instruction file to patch (default: {path})")
    parser.add_argument(
        "--skills-dir",
        default=skills_dir,
        help=(
            f"Skills directory to install the {SKILL_NAME} skill into (default: {skills_dir})"
            if skills_dir
            else argparse.SUPPRESS
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Show the diff without writing")
    parser.add_argument(
        "--print", dest="print_only", action="store_true", help="Print what would be installed and exit"
    )
    parser.set_defaults(handler=_cmd_install_instruction_async, binary=binary)

    remover = sub.add_parser(
        "remove-instruction",
        help="Remove memU's managed block from the host's global instruction file (the uninstall mirror)",
    )
    remover.add_argument("--path", default=path, help=f"Instruction file to unpatch (default: {path})")
    remover.add_argument("--dry-run", action="store_true", help="Show the diff without writing")
    remover.set_defaults(handler=_cmd_remove_instruction_async, binary=binary)
