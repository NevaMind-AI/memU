"""The inject seam's instruction: does patching a user's AGENTS.md stay safe?

The target file belongs to the *host*, not to memU, and may already hold a user's
own global instructions. These pin the three properties that protect it: existing
content survives, a re-run does not stack a second copy, and a changed
:data:`INSTRUCTION_TEMPLATE` upgrades in place rather than appending a stale twin.
"""

from __future__ import annotations

import pathlib

from memu.hosts import instruction
from memu.hosts.codex.cli import AGENTS_MD, build_parser

BINARY = "memu-codex"


def test_creates_file_when_absent(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "nested" / "AGENTS.md"
    changed, _ = instruction.install(path, BINARY)
    assert changed
    assert instruction.instruction(BINARY) in path.read_text(encoding="utf-8")


def test_preserves_existing_content(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "AGENTS.md"
    path.write_text("# My rules\n\nAlways use tabs.\n", encoding="utf-8")
    instruction.install(path, BINARY)

    text = path.read_text(encoding="utf-8")
    assert "Always use tabs." in text
    assert instruction.instruction(BINARY) in text
    # The user's content is backed up before we touch it.
    assert (tmp_path / "AGENTS.md.bak").read_text(encoding="utf-8") == "# My rules\n\nAlways use tabs.\n"


def test_install_is_idempotent(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "AGENTS.md"
    path.write_text("# My rules\n", encoding="utf-8")

    instruction.install(path, BINARY)
    first = path.read_text(encoding="utf-8")
    changed, diff = instruction.install(path, BINARY)

    assert not changed and not diff, "a re-run must be a no-op, not a second copy"
    assert path.read_text(encoding="utf-8") == first
    assert first.count(instruction.begin(BINARY)) == 1


def test_upgrade_replaces_in_place(monkeypatch, tmp_path: pathlib.Path) -> None:
    """The whole reason the block is marker-fenced: a later memU can update it."""
    path = tmp_path / "AGENTS.md"
    path.write_text("# My rules\n", encoding="utf-8")
    instruction.install(path, BINARY)

    monkeypatch.setattr(instruction, "INSTRUCTION_TEMPLATE", "## memU\n\nNew and improved.\n")
    changed, _ = instruction.install(path, BINARY)

    text = path.read_text(encoding="utf-8")
    assert changed
    assert "New and improved." in text
    assert "retrieve before answering" not in text, "the old block must be gone, not duplicated"
    assert text.count(instruction.begin(BINARY)) == 1
    assert "# My rules" in text


def test_each_host_manages_its_own_block(tmp_path: pathlib.Path) -> None:
    """Two hosts pointed at one file must not clobber each other's block."""
    path = tmp_path / "AGENTS.md"
    instruction.install(path, "memu-codex")
    instruction.install(path, "memu-claude-code")

    text = path.read_text(encoding="utf-8")
    assert text.count(instruction.begin("memu-codex")) == 1
    assert text.count(instruction.begin("memu-claude-code")) == 1
    assert "memu-codex retrieve" in text
    assert "memu-claude-code retrieve" in text


def test_patch_survives_a_file_with_no_trailing_newline() -> None:
    assert instruction.patch("no newline here", BINARY).startswith("no newline here\n\n")


def test_dry_run_writes_nothing(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "AGENTS.md"
    path.write_text("# My rules\n", encoding="utf-8")

    changed, diff = instruction.install(path, BINARY, dry_run=True)

    assert not changed
    assert diff, "a dry run still reports what it would do"
    assert path.read_text(encoding="utf-8") == "# My rules\n"
    assert not (tmp_path / "AGENTS.md.bak").exists()


def test_cli_defaults_to_the_codex_instruction_file() -> None:
    args = build_parser().parse_args(["install-instruction"])
    assert args.path == AGENTS_MD
    assert args.binary == BINARY
    assert callable(args.handler)


def test_instruction_names_the_llm_free_retrieval() -> None:
    """`memu retrieve` is LLM-routed — one LLM call per turn is what this avoids."""
    assert "memu-codex retrieve" in instruction.instruction(BINARY)
    assert "`memu retrieve" not in instruction.instruction(BINARY)


def test_remove_restores_user_content_byte_for_byte(tmp_path: pathlib.Path) -> None:
    """The uninstall promise: an install/remove round-trip is invisible."""
    original = "# My rules\n\nAlways use tabs.\n"
    path = tmp_path / "AGENTS.md"
    path.write_text(original, encoding="utf-8")
    instruction.install(path, BINARY)

    changed, diff = instruction.remove(path, BINARY)

    assert changed and diff
    assert path.read_text(encoding="utf-8") == original


def test_remove_leaves_a_block_only_file_empty(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "AGENTS.md"
    instruction.install(path, BINARY)  # install created the file: block only

    changed, _ = instruction.remove(path, BINARY)

    assert changed
    assert path.read_text(encoding="utf-8") == ""


def test_remove_without_block_or_file_is_a_noop(tmp_path: pathlib.Path) -> None:
    assert instruction.remove(tmp_path / "absent.md", BINARY) == (False, "")

    path = tmp_path / "AGENTS.md"
    path.write_text("# Mine\n", encoding="utf-8")
    changed, diff = instruction.remove(path, BINARY)

    assert not changed and not diff
    assert path.read_text(encoding="utf-8") == "# Mine\n"


def test_remove_only_takes_this_hosts_block(tmp_path: pathlib.Path) -> None:
    """Uninstalling one host must not tear out another host's block."""
    path = tmp_path / "AGENTS.md"
    instruction.install(path, "memu-codex")
    instruction.install(path, "memu-claude-code")

    instruction.remove(path, "memu-codex")

    text = path.read_text(encoding="utf-8")
    assert instruction.begin("memu-codex") not in text
    assert text.count(instruction.begin("memu-claude-code")) == 1


def test_remove_dry_run_writes_nothing(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "AGENTS.md"
    path.write_text("# My rules\n", encoding="utf-8")
    instruction.install(path, BINARY)
    before = path.read_text(encoding="utf-8")

    changed, diff = instruction.remove(path, BINARY, dry_run=True)

    assert not changed
    assert diff, "a dry run still reports what it would do"
    assert path.read_text(encoding="utf-8") == before


def test_remove_backs_up_before_rewriting(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "AGENTS.md"
    path.write_text("# My rules\n", encoding="utf-8")
    instruction.install(path, BINARY)
    with_block = path.read_text(encoding="utf-8")

    instruction.remove(path, BINARY)

    assert (tmp_path / "AGENTS.md.bak").read_text(encoding="utf-8") == with_block


def test_cli_registers_remove_instruction() -> None:
    args = build_parser().parse_args(["remove-instruction"])
    assert args.path == AGENTS_MD
    assert args.binary == BINARY
    assert callable(args.handler)
