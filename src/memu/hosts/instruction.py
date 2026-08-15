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
import contextlib
import difflib
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from memu.hosts import templates

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
query, each naming in `source_file` the document it was cut from. `files` are
those synthesized documents — broader, and worth consulting when a segment reads
as relevant but is too thin to act on; find one by matching a segment's
`source_file` to it. Each file gives you a summary plus either a `path` to open
when you need the full text or, if its file is unavailable, the text inline.
`resources` are files on the user's own machine that look related, each a `path`
plus a summary. Work from the summaries; open a `path` only when you need what it
leaves out.
"""

# The body is a ``{body}`` slot rather than baked in, so the same document can be
# rendered with either the embedded :data:`RETRIEVAL_BODY` or the body carved out
# of the server's current skill (:mod:`memu.hosts.templates`) — see :func:`_body`,
# :func:`_skill_body`, and :func:`refresh`.
INSTRUCTION_TEMPLATE = """\
## memU — retrieve before answering

Before answering:

{body}"""

SKILL_INSTRUCTION_TEMPLATE = """\
## memU — retrieve before answering

Before answering, use the `{skill}` skill to pull any relevant memory into
context. It fails open: if nothing comes back, answer normally.
"""

SKILL_TEMPLATE = """\
---
name: {name}
description: Retrieve the user's durable memory from memU before answering. Run it
  at the start of every turn, even when the request seems self-contained — it is
  one cheap command and fails open; skipping it means answering without what the
  user already told you.
---

# Retrieve from memU before answering

{body}"""


def begin(binary: str) -> str:
    """The opening marker, naming the host binary that manages the block."""
    return BEGIN_TEMPLATE.format(binary=binary)


def _skill_body(skill_text: str) -> str:
    """The retrieval body carved out of a full ``SKILL.md`` document.

    The server now serves the whole skill — YAML frontmatter, ``# Retrieve…``
    heading, and body (see :func:`refresh`). A skill host writes that document
    verbatim; an inline host wants only the *procedure* to slot into its own
    :data:`INSTRUCTION_TEMPLATE`, under its own heading. So strip the leading
    frontmatter block and the first H1, leaving the body (still carrying
    ``{binary}``, which :func:`_body` fills).
    """
    without_frontmatter = re.sub(r"\A---\n.*?\n---\n+", "", skill_text, count=1, flags=re.DOTALL)
    return re.sub(r"\A#[^\n]*\n+", "", without_frontmatter, count=1)


def _body(binary: str, skill_text: str | None) -> str:
    """The retrieval body with ``{binary}`` filled: from the server skill, else embedded.

    ``skill_text`` is a full skill document as a caller fetched it from the server;
    its body is carved out with :func:`_skill_body`. ``None`` means the embedded
    copy. ``{binary}`` is filled here, before the body is slotted into a document,
    so a body that happens to contain other braces stays safe — ``.format`` never
    re-parses a value it substituted in.
    """
    body = RETRIEVAL_BODY if skill_text is None else _skill_body(skill_text)
    return body.format(binary=binary)


def skill_document(binary: str, *, skill_text: str | None = None) -> str:
    """The ``SKILL.md`` as written to disk, telling the agent how to retrieve.

    ``skill_text`` is the server's current full skill document, written verbatim
    with only ``{binary}`` filled; ``None`` renders the embedded skill.
    """
    if skill_text is not None:
        return skill_text.format(binary=binary)
    return SKILL_TEMPLATE.format(name=SKILL_NAME, body=_body(binary, None))


def instruction(binary: str, *, skill: bool = False, skill_text: str | None = None) -> str:
    """The instruction text, telling the agent to run this host's ``retrieve``.

    ``skill=True`` returns the short pointer for hosts where :func:`install_skill`
    has put the detail in a skill; otherwise the full inline text. ``skill_text``
    overrides the embedded retrieval body with the body carved out of a
    server-fetched skill (ignored for the pointer, which carries no body).
    """
    if skill:
        return SKILL_INSTRUCTION_TEMPLATE.format(skill=SKILL_NAME, binary=binary)
    return INSTRUCTION_TEMPLATE.format(body=_body(binary, skill_text))


def block(binary: str, *, skill: bool = False, skill_text: str | None = None) -> str:
    """The managed block exactly as it is written to disk, markers included."""
    return f"{begin(binary)}\n{instruction(binary, skill=skill, skill_text=skill_text)}{END}\n"


def _block_re(binary: str) -> re.Pattern[str]:
    return re.compile(
        rf"^{re.escape(begin(binary))}\n.*?^{re.escape(END)}\n?",
        re.DOTALL | re.MULTILINE,
    )


def patch(current: str, binary: str, *, skill: bool = False, skill_text: str | None = None) -> str:
    """Return ``current`` with the managed block installed — replaced, or appended.

    Pure, so the interesting half of :func:`install` is testable without a
    filesystem. Idempotent by construction: the markers delimit what memU owns, so
    a second call replaces the first call's block rather than stacking another
    copy, and text outside them survives untouched.
    """
    pattern = _block_re(binary)
    if pattern.search(current):
        return pattern.sub(lambda _: block(binary, skill=skill, skill_text=skill_text), current, count=1)
    if current and not current.endswith("\n"):
        current += "\n"
    separator = "\n" if current else ""
    return f"{current}{separator}{block(binary, skill=skill, skill_text=skill_text)}"


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
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(updated)
        if path.exists():
            shutil.copymode(path, temporary)
        os.replace(temporary, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise
    return True, diff


def install(
    path: Path, binary: str, *, skill: bool = False, skill_text: str | None = None, dry_run: bool = False
) -> tuple[bool, str]:
    """Install the managed block into ``path``. Returns ``(changed, diff)``.

    Creates the file (and its parent) if absent, and backs up any existing content
    to ``<path>.bak`` before rewriting it — the target belongs to the *host*, not
    to memU, and may hold instructions that have nothing to do with us.

    ``skill`` installs the short block that points at :func:`install_skill`'s skill
    instead of the full inline text; pass it only when that skill is being
    installed too, or the block points at nothing. ``skill_text`` overrides the
    embedded retrieval body (for an inline host being refreshed from the server's
    current skill).
    """
    path = path.expanduser()
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    return _write(path, patch(current, binary, skill=skill, skill_text=skill_text), backup=True, dry_run=dry_run)


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


def install_skill(
    skills_dir: Path, binary: str, *, skill_text: str | None = None, dry_run: bool = False
) -> tuple[bool, str]:
    """Install the retrieval skill under ``skills_dir``. Returns ``(changed, diff)``.

    Unlike the instruction file, ``<skills_dir>/memu-retrieve/`` is memU's own —
    nothing of the user's lives there — so it is overwritten whole rather than
    marker-fenced and backed up. Same upgrade story either way: re-run and the
    release's text replaces the installed one. ``skill_text`` overrides the
    embedded skill with the server's current full document (for a skill host being
    refreshed from the server).
    """
    return _write(skill_path(skills_dir), skill_document(binary, skill_text=skill_text), backup=False, dry_run=dry_run)


def remove_skill(skills_dir: Path, *, dry_run: bool = False) -> tuple[bool, str]:
    """Remove the retrieval skill under ``skills_dir``. Returns ``(changed, diff)``.

    The uninstall-side mirror of :func:`install_skill`. Because
    ``<skills_dir>/memu-retrieve/`` is memU's own — written whole on install, with
    nothing of the user's inside — it is removed whole rather than edited, and no
    ``.bak`` is left (a reinstall rewrites it from the template, so a backup would
    buy nothing). Its ``SKILL.md`` is the marker that the directory is ours to take
    back: a directory missing that file, or absent entirely, is already the desired
    end state — a clean no-op, never an error — so a same-named directory the user
    created without memU's skill in it is left untouched.
    """
    target = skill_path(skills_dir)
    if not target.is_file():
        return False, ""
    directory = target.parent
    diff = f"removed {directory}/\n"
    if dry_run:
        return False, diff
    shutil.rmtree(directory)
    return True, diff


def refresh(path: Path, binary: str, *, skills_dir: Path | None = None) -> list[tuple[Path, bool]]:
    """Refresh an already-installed retrieval procedure from the server, in place.

    The scheduled counterpart to :func:`install`: the bridging run calls this so
    the installed copy tracks server improvements, while the per-turn retrieve
    hook never touches the network. The server serves the full skill document; this
    rewrites whatever holds the retrieval procedure — the ``SKILL.md`` on a skill
    host with that document verbatim, the inline managed block on an inline host
    with the body carved out of it (:func:`_skill_body`) — from
    :mod:`memu.hosts.templates`'s current server copy.

    Two properties matter here and differ from :func:`install`:

    * **Skip, never downgrade.** On an unreachable or malformed server the fetch
      is ``None`` and this writes nothing, so a transient outage leaves the
      already-installed (newer) copy in place instead of overwriting it with the
      embedded text. This is *why* the retrieval skill needs no cache of its own:
      the installed file already is the last-good.
    * **Refresh, never bootstrap.** With nothing installed here yet, it does
      nothing — installing is ``install-instruction``'s job. A scheduled run must
      not silently create files the user never asked for.

    Returns ``(target, changed)`` for each file touched — empty when it skipped.
    """
    skill_text = templates.fetch(templates.RETRIEVAL_SKILL)
    if skill_text is None:
        return []
    if skills_dir is not None:
        target = skill_path(skills_dir)
        if not target.is_file():
            return []
        changed, _ = install_skill(skills_dir, binary, skill_text=skill_text)
        return [(target, changed)]
    target = path.expanduser()
    if not target.is_file() or not _block_re(binary).search(target.read_text(encoding="utf-8")):
        return []
    changed, _ = install(path, binary, skill=False, skill_text=skill_text)
    return [(target, changed)]


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
    # An explicit, one-off, latency-tolerant command, so it pulls the server's
    # current retrieval skill here (fail-open to embedded on any failure); the
    # scheduled `refresh` keeps it current afterwards.
    skill_text = templates.fetch(templates.RETRIEVAL_SKILL)
    if args.print_only:
        if skills_dir is not None:
            print(f"# {skill_path(skills_dir)}\n\n{skill_document(args.binary, skill_text=skill_text)}")
        print(block(args.binary, skill=skill, skill_text=skill_text), end="")
        return 0

    # The skill goes in first: between the two writes, an instruction block naming
    # a skill that is not there yet is the only order that can mislead an agent.
    if skills_dir is not None:
        changed, diff = install_skill(skills_dir, args.binary, skill_text=skill_text, dry_run=args.dry_run)
        _report(skill_path(skills_dir), changed, diff, dry_run=args.dry_run)

    path = Path(args.path)
    changed, diff = install(path, args.binary, skill=skill, skill_text=skill_text, dry_run=args.dry_run)
    _report(path.expanduser(), changed, diff, dry_run=args.dry_run)

    # Migrate only when the host's default target is in use. An explicit --path
    # describes a separate profile or workspace and must not rewrite files under
    # the default home. Install the new target first so a failed write can never
    # remove the user's only working retrieval instruction.
    if args.path == args.default_instruction_path:
        for legacy_text in args.legacy_paths:
            legacy = Path(legacy_text)
            if legacy.expanduser() == path.expanduser():
                continue
            legacy_changed, legacy_diff = remove(legacy, args.binary, dry_run=args.dry_run)
            if legacy_diff:
                _report(legacy.expanduser(), legacy_changed, legacy_diff, dry_run=args.dry_run)
    return 0


def _cmd_remove_instruction(args: argparse.Namespace) -> int:
    paths = [Path(args.path)]
    if args.path == args.default_instruction_path:
        paths.extend(Path(path) for path in args.legacy_paths)

    reported = False
    seen: set[Path] = set()
    for path in paths:
        expanded = path.expanduser()
        if expanded in seen:
            continue
        seen.add(expanded)
        changed, diff = remove(path, args.binary, dry_run=args.dry_run)
        if not diff:
            continue
        reported = True
        _report(expanded, changed, diff, dry_run=args.dry_run)

    # The skill comes out after the instruction that points at it — the inverse of
    # install's skill-first order (an instruction naming a skill that is not there
    # is the one state that misleads an agent), so no live pointer ever dangles.
    # Skill hosts only; inline hosts pass an empty --skills-dir and skip this.
    if args.skills_dir:
        skills_dir = Path(args.skills_dir)
        changed, diff = remove_skill(skills_dir, dry_run=args.dry_run)
        if diff:
            reported = True
            _report(skill_path(skills_dir), changed, diff, dry_run=args.dry_run)

    if not reported:
        print(f"{Path(args.path)}: no managed block to remove")
    return 0


async def _cmd_install_instruction_async(args: argparse.Namespace) -> int:
    """The host CLIs dispatch coroutines; this command needs no I/O loop of its own."""
    return _cmd_install_instruction(args)


async def _cmd_remove_instruction_async(args: argparse.Namespace) -> int:
    """The host CLIs dispatch coroutines; this command needs no I/O loop of its own."""
    return _cmd_remove_instruction(args)


def register(
    sub: Any,
    *,
    path: str,
    binary: str,
    skills_dir: str = "",
    legacy_paths: tuple[str, ...] = (),
) -> None:
    """Add ``install-instruction`` to a host CLI, bound to that host's ``path``.

    ``binary`` is the host adapter's own command name (``memu-codex``, …) — it is
    what the installed instruction tells the agent to run.

    ``skills_dir`` is the host's skills directory (``~/.claude/skills``, …), if it
    has one. Given it, the command installs the retrieval skill there and patches
    ``path`` with a two-sentence pointer to it; left empty, it patches ``path``
    with the full text and writes no skill.

    ``legacy_paths`` names earlier defaults owned by the same host adapter. A
    default-path install removes this binary's managed block from them only after
    the current target is installed; default-path uninstall checks both. Custom
    ``--path`` calls leave them alone.
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
    parser.set_defaults(
        handler=_cmd_install_instruction_async,
        binary=binary,
        default_instruction_path=path,
        legacy_paths=legacy_paths,
    )

    remover = sub.add_parser(
        "remove-instruction",
        help=(
            "Remove memU's managed block from the host's global instruction file — and, on a "
            "skill host, the retrieval skill it points at (the uninstall mirror)"
        ),
    )
    remover.add_argument("--path", default=path, help=f"Instruction file to unpatch (default: {path})")
    remover.add_argument(
        "--skills-dir",
        default=skills_dir,
        help=(
            f"Skills directory the {SKILL_NAME} skill was installed into (default: {skills_dir})"
            if skills_dir
            else argparse.SUPPRESS
        ),
    )
    remover.add_argument("--dry-run", action="store_true", help="Show the diff without writing")
    remover.set_defaults(
        handler=_cmd_remove_instruction_async,
        binary=binary,
        default_instruction_path=path,
        legacy_paths=legacy_paths,
    )
