"""Probe an agent installation: does memorization work here, does retrieval?

The generic adapter's contract with an unknown agent is two questions, asked in
order (the order the seams matter in):

1. **Memorization (the record seam).** Is there a session log on disk, and do
   its records sniff as one of the known JSONL dialects? Found and recognized —
   the bridging task can mine it, memorization works. A log in a container we
   cannot read (SQLite, editor state) is reported as such rather than silently
   skipped.
2. **Retrieval (the inject seam).** No session log is not the end: if the agent
   loads an instruction file (``AGENTS.md``, ``CLAUDE.md``, ``SOUL.md``, …),
   ``install-instruction --path`` can still plant the standing retrieve
   instruction, and retrieval works even though nothing is mined from this
   agent.

The verdicts are what ``memu-agent detect`` prints. Everything here is
read-only probing — nothing is written.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from memu.hosts.base import RecordKind
from memu.hosts.generic.sessions import GenericTranscriptSource

INSTRUCTION_NAMES = (
    "AGENTS.md",
    "agents.md",
    "AGENT.md",
    "CLAUDE.md",
    "SOUL.md",
    "GEMINI.md",
    "QWEN.md",
    ".cursorrules",
)
"""Instruction-file names the ecosystem's agents load into every session."""

DEDICATED = {
    ".codex": "memu-codex",
    ".claude": "memu-claude-code",
    ".cursor": "memu-cursor",
    ".openclaw": "memu-openclaw",
    ".hermes": "memu-hermes",
}
"""Agent dirs that already have a dedicated adapter — detect points at it."""

_SKIP_DIRS = frozenset({
    ".Trash",
    ".cache",
    ".cargo",
    ".config",
    ".docker",
    ".git",
    ".gradle",
    ".local",
    ".m2",
    ".npm",
    ".nvm",
    ".ollama",
    ".pyenv",
    ".rustup",
    ".ssh",
    ".venv",
    ".vscode",
    "node_modules",
})
"""Home-directory entries that are tooling state, not agents."""

_MAX_FILES_PER_DIR = 2000
_SAMPLE_FILES = 3
_SAMPLE_LINES = 200


@dataclass
class Probe:
    """What one directory yielded, and the two verdicts drawn from it."""

    path: Path
    session_files: list[Path] = field(default_factory=list)
    sampled: int = 0
    messages: int = 0
    tools: int = 0
    sqlite_files: list[Path] = field(default_factory=list)
    instruction_files: list[Path] = field(default_factory=list)
    dedicated: str | None = None

    @property
    def memorization(self) -> bool:
        """Sessions found *and* their records sniff as conversation."""
        return self.messages > 0

    @property
    def retrieval(self) -> bool:
        """An instruction file the agent loads exists — the inject seam has a home."""
        return bool(self.instruction_files)


def _iter_files(root: Path) -> list[Path]:
    """Files under ``root``, capped so a huge non-agent dir cannot stall detect."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for name in filenames:
            found.append(Path(dirpath) / name)
            if len(found) >= _MAX_FILES_PER_DIR:
                return found
    return found


def probe(path: str | Path) -> Probe:
    """Probe one directory. Read-only; safe on anything."""
    root = Path(os.path.expanduser(str(path)))
    result = Probe(path=root, dedicated=DEDICATED.get(root.name))
    if not root.is_dir():
        return result

    files = _iter_files(root)
    result.session_files = sorted(
        (f for f in files if f.suffix == ".jsonl"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    result.sqlite_files = [f for f in files if f.suffix in (".db", ".sqlite", ".sqlite3", ".vscdb")]
    # An instruction file the agent actually loads sits at the top of its dir
    # (or one level down, like OpenClaw's workspace/AGENTS.md). Anything deeper
    # is plugin/checkout content wearing the same name — never the inject target.
    instruction_candidates = [f for f in files if f.name in INSTRUCTION_NAMES and len(f.relative_to(root).parts) <= 2]
    result.instruction_files = sorted(instruction_candidates, key=lambda f: len(f.relative_to(root).parts))

    source = GenericTranscriptSource(root)
    for session in result.session_files[:_SAMPLE_FILES]:
        try:
            records = source.read_records(session)[:_SAMPLE_LINES]
        except (OSError, UnicodeDecodeError):
            continue
        for record in records:
            result.sampled += 1
            kind = source.classify(record)
            if kind is RecordKind.MESSAGE:
                result.messages += 1
            elif kind is RecordKind.TOOL:
                result.tools += 1
    return result


def scan_home(home: str | Path = "~") -> list[Probe]:
    """Probe every plausible agent dir under ``home``, dedicated hosts included."""
    root = Path(os.path.expanduser(str(home)))
    probes = []
    for entry in sorted(root.glob(".*")):
        if not entry.is_dir() or entry.name in _SKIP_DIRS:
            continue
        candidate = probe(entry)
        if candidate.session_files or candidate.instruction_files or candidate.sqlite_files or candidate.dedicated:
            probes.append(candidate)
    return probes


def _shorten(path: Path) -> str:
    home = str(Path.home())
    text = str(path)
    return "~" + text[len(home) :] if text.startswith(home) else text


def render(result: Probe) -> str:
    """One directory's verdicts, as ``detect`` prints them."""
    lines = [f"{_shorten(result.path)}"]

    if result.dedicated:
        lines.append(f"  dedicated adapter: use `{result.dedicated}` (docs: `{result.dedicated} docs install`)")

    if result.memorization:
        recognized = result.messages + result.tools
        lines.append(
            f"  memorization: works — {len(result.session_files)} session file(s), "
            f"{recognized}/{result.sampled} sampled record(s) recognized "
            f"({result.messages} conversation, {result.tools} tool)"
        )
    elif result.session_files:
        lines.append(
            f"  memorization: no — {len(result.session_files)} .jsonl file(s) found but no record "
            f"matched a known dialect (not a conversation log, or a new shape)"
        )
    elif result.sqlite_files:
        lines.append(
            f"  memorization: no — sessions likely live in {_shorten(result.sqlite_files[0])} "
            f"(SQLite; needs a dedicated adapter, like memu-hermes has)"
        )
    else:
        lines.append("  memorization: no — no session log found")

    if result.retrieval:
        target = result.instruction_files[0]
        lines.append(
            f"  retrieval: works — instruction file {_shorten(target)} "
            f"(install with `memu-agent install-instruction --path {_shorten(target)}`)"
        )
    else:
        lines.append(
            "  retrieval: no instruction file found — if this agent reads AGENTS.md from the "
            "project root, run `memu-agent install-instruction` inside each project"
        )
    return "\n".join(lines)
