"""The inject seam's instruction: does patching a user's AGENTS.md stay safe?

The target file belongs to the *host*, not to memU, and may already hold a user's
own global instructions. These pin the three properties that protect it: existing
content survives, a re-run does not stack a second copy, and a changed
:data:`INSTRUCTION_TEMPLATE` upgrades in place rather than appending a stale twin.

The second half pins the split: on a host with skills the procedure lives in a
skill and the instruction file gets a pointer; on a host without one, nothing
about today's behaviour moves.
"""

from __future__ import annotations

import pathlib

from memu.hosts import instruction
from memu.hosts.codex.cli import AGENTS_MD, SKILLS_DIR, build_parser

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
    assert args.skills_dir == SKILLS_DIR
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


def test_skill_carries_the_procedure_and_names_the_host_binary() -> None:
    document = instruction.skill_document(BINARY)
    assert document.startswith(f"---\nname: {instruction.SKILL_NAME}\n")
    assert "description:" in document, "the host reads the frontmatter to decide whether to open it"
    assert "memu-codex retrieve" in document, "the skill is where the runnable command now lives"
    assert "`memu retrieve" not in document


def test_skill_block_points_at_the_skill_instead_of_carrying_the_procedure() -> None:
    """The whole point of the split: what sits in every turn's context stays small."""
    pointer = instruction.instruction(BINARY, skill=True)
    assert instruction.SKILL_NAME in pointer
    assert "retrieve" in pointer
    assert "segments" not in pointer, "the result legend belongs in the skill, not in every turn"
    assert len(pointer.splitlines()) < len(instruction.instruction(BINARY).splitlines())


def test_install_skill_writes_the_skill_where_the_host_looks(tmp_path: pathlib.Path) -> None:
    changed, diff = instruction.install_skill(tmp_path / "skills", BINARY)

    path = tmp_path / "skills" / instruction.SKILL_NAME / "SKILL.md"
    assert changed and diff
    assert path.read_text(encoding="utf-8") == instruction.skill_document(BINARY)


def test_install_skill_is_idempotent_then_upgrades_in_place(tmp_path: pathlib.Path, monkeypatch) -> None:
    skills = tmp_path / "skills"
    instruction.install_skill(skills, BINARY)

    changed, diff = instruction.install_skill(skills, BINARY)
    assert not changed and not diff, "a re-run must be a no-op"

    monkeypatch.setattr(instruction, "SKILL_TEMPLATE", "---\nname: memu-retrieve\n---\n\nNew and improved.\n")
    changed, _ = instruction.install_skill(skills, BINARY)
    text = (skills / instruction.SKILL_NAME / "SKILL.md").read_text(encoding="utf-8")
    assert changed
    assert text == "---\nname: memu-retrieve\n---\n\nNew and improved.\n", "an upgrade replaces it whole"


def test_install_skill_dry_run_writes_nothing(tmp_path: pathlib.Path) -> None:
    changed, diff = instruction.install_skill(tmp_path / "skills", BINARY, dry_run=True)

    assert not changed
    assert diff, "a dry run still reports what it would do"
    assert not (tmp_path / "skills").exists()


def test_a_skill_host_upgrades_from_the_old_inline_block(tmp_path: pathlib.Path) -> None:
    """Users installed before the split have the full text in their file already."""
    path = tmp_path / "AGENTS.md"
    path.write_text("# My rules\n", encoding="utf-8")
    instruction.install(path, BINARY)
    assert "segments" in path.read_text(encoding="utf-8")

    changed, _ = instruction.install(path, BINARY, skill=True)

    text = path.read_text(encoding="utf-8")
    assert changed
    assert instruction.SKILL_NAME in text
    assert "segments" not in text, "the superseded inline procedure must be gone, not left beside the pointer"
    assert text.count(instruction.begin(BINARY)) == 1
    assert "# My rules" in text


def test_cli_installs_skill_and_pointer_together_for_a_skill_host(tmp_path: pathlib.Path) -> None:
    args = build_parser().parse_args([
        "install-instruction",
        "--path",
        str(tmp_path / "AGENTS.md"),
        "--skills-dir",
        str(tmp_path / "skills"),
    ])
    assert instruction._cmd_install_instruction(args) == 0

    assert (tmp_path / "skills" / instruction.SKILL_NAME / "SKILL.md").is_file()
    assert instruction.SKILL_NAME in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")


def test_cli_without_a_skills_dir_keeps_the_full_text_and_writes_no_skill(tmp_path: pathlib.Path) -> None:
    """Hosts with no skills mechanism must not regress into pointing at nothing."""
    args = build_parser().parse_args(["install-instruction", "--path", str(tmp_path / "AGENTS.md"), "--skills-dir", ""])
    assert instruction._cmd_install_instruction(args) == 0

    text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "memu-codex retrieve" in text and "segments" in text
    assert not (tmp_path / "skills").exists()
