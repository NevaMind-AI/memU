"""The inject seam's instruction: does patching a user's AGENTS.md stay safe?

The target file belongs to the *host*, not to memU, and may already hold a user's
own global instructions. These pin the three properties that protect it: existing
content survives, a re-run does not stack a second copy, and a changed
:data:`INSTRUCTION` upgrades in place rather than appending a stale twin.
"""

from __future__ import annotations

import pathlib

from memu.hosts import instruction
from memu.hosts.codex.cli import AGENTS_MD, build_parser


def test_creates_file_when_absent(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "nested" / "AGENTS.md"
    changed, _ = instruction.install(path)
    assert changed
    assert instruction.INSTRUCTION in path.read_text()


def test_preserves_existing_content(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "AGENTS.md"
    path.write_text("# My rules\n\nAlways use tabs.\n")
    instruction.install(path)

    text = path.read_text()
    assert "Always use tabs." in text
    assert instruction.INSTRUCTION in text
    # The user's content is backed up before we touch it.
    assert (tmp_path / "AGENTS.md.bak").read_text() == "# My rules\n\nAlways use tabs.\n"


def test_install_is_idempotent(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "AGENTS.md"
    path.write_text("# My rules\n")

    instruction.install(path)
    first = path.read_text()
    changed, diff = instruction.install(path)

    assert not changed and not diff, "a re-run must be a no-op, not a second copy"
    assert path.read_text() == first
    assert first.count(instruction.BEGIN) == 1


def test_upgrade_replaces_in_place(monkeypatch, tmp_path: pathlib.Path) -> None:
    """The whole reason the block is marker-fenced: a later memU can update it."""
    path = tmp_path / "AGENTS.md"
    path.write_text("# My rules\n")
    instruction.install(path)

    monkeypatch.setattr(instruction, "INSTRUCTION", "## memU\n\nNew and improved.\n")
    changed, _ = instruction.install(path)

    text = path.read_text()
    assert changed
    assert "New and improved." in text
    assert "retrieve before answering" not in text, "the old block must be gone, not duplicated"
    assert text.count(instruction.BEGIN) == 1
    assert "# My rules" in text


def test_patch_survives_a_file_with_no_trailing_newline() -> None:
    assert instruction.patch("no newline here").startswith("no newline here\n\n")


def test_dry_run_writes_nothing(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "AGENTS.md"
    path.write_text("# My rules\n")

    changed, diff = instruction.install(path, dry_run=True)

    assert not changed
    assert diff, "a dry run still reports what it would do"
    assert path.read_text() == "# My rules\n"
    assert not (tmp_path / "AGENTS.md.bak").exists()


def test_cli_defaults_to_the_codex_instruction_file() -> None:
    args = build_parser().parse_args(["install-instruction"])
    assert args.path == AGENTS_MD
    assert callable(args.handler)


def test_instruction_names_the_llm_free_retrieval() -> None:
    """`memu retrieve` is LLM-routed — one LLM call per turn is what this avoids."""
    assert "memu-codex retrieve" in instruction.INSTRUCTION
    assert "`memu retrieve" not in instruction.INSTRUCTION
