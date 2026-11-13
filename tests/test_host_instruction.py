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

import argparse
import pathlib
import subprocess
import sys
import textwrap

import pytest

from memu.hosts import instruction
from memu.hosts.codex.cli import AGENTS_MD, SKILLS_DIR, build_parser
from memu.hosts.host_cli import build_parser as build_host_parser
from memu.hosts.workbuddy.cli import MEMORY_MD as WORKBUDDY_LEGACY_MEMORY_MD
from memu.hosts.workbuddy.cli import SOUL_MD as WORKBUDDY_SOUL_MD
from memu.hosts.workbuddy.cli import SPEC as WORKBUDDY_SPEC

BINARY = "memu-codex"
WORKBUDDY_BINARY = "memu-workbuddy"


def _migration_parser(current: pathlib.Path, legacy: pathlib.Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    instruction.register(
        sub,
        path=str(current),
        binary=WORKBUDDY_BINARY,
        legacy_paths=(str(legacy),),
    )
    return parser


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


def test_rewrite_failure_leaves_the_instruction_file_intact(monkeypatch, tmp_path: pathlib.Path) -> None:
    path = tmp_path / "AGENTS.md"
    path.write_text("# My rules\n", encoding="utf-8")

    def fail_replace(source: str, destination: pathlib.Path) -> None:
        raise OSError

    monkeypatch.setattr(instruction.os, "replace", fail_replace)

    with pytest.raises(OSError):
        instruction._write(path, "# Updated rules\n", backup=False, dry_run=False)

    assert path.read_text(encoding="utf-8") == "# My rules\n"
    assert not list(tmp_path.glob(".tmp-*"))


def test_rewrite_preserves_an_instruction_symlink(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "dotfiles" / "AGENTS.md"
    target.parent.mkdir()
    target.write_text("# My rules\n", encoding="utf-8")
    path = tmp_path / "AGENTS.md"
    path.symlink_to(target)

    instruction.install(path, BINARY)

    assert path.is_symlink()
    assert instruction.instruction(BINARY) in target.read_text(encoding="utf-8")


def test_cli_defaults_to_the_codex_instruction_file() -> None:
    args = build_parser().parse_args(["install-instruction"])
    assert args.path == AGENTS_MD
    assert args.skills_dir == SKILLS_DIR
    assert args.binary == BINARY
    assert callable(args.handler)


def test_hermes_is_an_inline_host() -> None:
    from memu.hosts.hermes.cli import SPEC

    assert SPEC.skills_dir == ""
    text = instruction.instruction("memu-hermes")
    assert "retrieve relevant memory on demand" in text
    assert "Greetings" in text
    assert "memu-hermes retrieve" in text
    assert "before answering" not in text


@pytest.mark.parametrize("dry_run,custom", [(False, False), (True, False), (False, True)])
def test_hermes_inline_install_migrates_safely(tmp_path, monkeypatch, dry_run, custom):
    from dataclasses import replace

    from memu.hosts.hermes.cli import SPEC

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr(instruction.templates, "fetch", lambda *_: pytest.fail("Hermes uses its local policy"))
    soul = tmp_path / "SOUL.md"
    soul.write_text("User identity\n", encoding="utf-8")
    legacy = instruction.skill_path(tmp_path / "skills")
    legacy.parent.mkdir(parents=True)
    legacy.write_text(instruction.skill_document("memu-hermes"), encoding="utf-8")
    parser = build_host_parser(replace(SPEC, instruction_path=str(soul)))
    argv = ["install-instruction"]
    target = tmp_path / "other" / "SOUL.md" if custom else soul
    if custom:
        argv += ["--path", str(target)]
    if dry_run:
        argv += ["--dry-run"]
    args = parser.parse_args(argv)
    assert instruction._cmd_install_instruction(args) == 0
    if dry_run:
        assert soul.read_text(encoding="utf-8") == "User identity\n"
        assert legacy.exists()
        return
    text = target.read_text(encoding="utf-8")
    assert "retrieve relevant memory on demand" in text
    assert instruction._cmd_install_instruction(args) == 0
    assert target.read_text(encoding="utf-8") == text
    assert legacy.exists() is custom
    if custom:
        assert soul.read_text(encoding="utf-8") == "User identity\n"
    else:
        assert text.startswith("User identity\n")
        assert instruction.refresh(soul, "memu-hermes") == [(soul, False)]
        remove_args = parser.parse_args(["remove-instruction"])
        assert instruction._cmd_remove_instruction(remove_args) == 0
        assert soul.read_text(encoding="utf-8") == "User identity\n"
        assert not legacy.exists()


@pytest.mark.parametrize("profile", ["windows_default", "override", "suffix", "windows_fallback"])
def test_hermes_cli_targets_active_soul_after_import(tmp_path, monkeypatch, profile):
    from memu.hosts.hermes.cli import main

    monkeypatch.setattr("memu.hosts.hermes.sessions.sys.platform", "win32")
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path / "User")
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.delenv("HERMES_DATA_DIR_SUFFIX", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    target = tmp_path / "Local" / "hermes" / "SOUL.md"
    if profile == "override":
        monkeypatch.setenv("MEMU_TEST_PROFILE_ROOT", str(tmp_path / "Profiles"))
        monkeypatch.setenv("HERMES_HOME", "$MEMU_TEST_PROFILE_ROOT/Research Hermes")
        target = tmp_path / "Profiles" / "Research Hermes" / "SOUL.md"
    elif profile == "suffix":
        monkeypatch.setenv("HERMES_DATA_DIR_SUFFIX", "-test")
        target = tmp_path / "Local" / "hermes-test" / "SOUL.md"
    elif profile == "windows_fallback":
        monkeypatch.delenv("LOCALAPPDATA")
        target = tmp_path / "User" / "AppData" / "Local" / "hermes" / "SOUL.md"
    target.parent.mkdir(parents=True)
    target.write_text("User identity\n", encoding="utf-8")
    assert main(["install-instruction", "--dry-run"]) == 0
    assert target.read_text(encoding="utf-8") == "User identity\n"
    assert main(["install-instruction"]) == 0
    text = target.read_text(encoding="utf-8")
    assert "retrieve relevant memory on demand" in text
    assert main(["install-instruction"]) == 0
    assert target.read_text(encoding="utf-8") == text
    assert main(["remove-instruction"]) == 0
    assert target.read_text(encoding="utf-8") == "User identity\n"
    assert not (tmp_path / "User" / ".hermes" / "SOUL.md").exists()
    assert not (tmp_path / "Roaming" / "hermes" / "SOUL.md").exists()


def test_hermes_custom_remove_preserves_default_profile(tmp_path, monkeypatch):
    from memu.hosts.hermes.cli import main

    home = tmp_path / "default"
    monkeypatch.setenv("HERMES_HOME", str(home))
    soul = home / "SOUL.md"
    custom = tmp_path / "other" / "SOUL.md"
    instruction.install(soul, "memu-hermes")
    instruction.install(custom, "memu-hermes")
    default_text = soul.read_text(encoding="utf-8")
    legacy = instruction.skill_path(home / "skills")
    legacy.parent.mkdir(parents=True)
    legacy.write_text("Legacy retrieval procedure", encoding="utf-8")
    assert main(["remove-instruction", "--path", str(custom), "--dry-run"]) == 0
    assert instruction.begin("memu-hermes") in custom.read_text(encoding="utf-8")
    assert main(["remove-instruction", "--path", str(custom)]) == 0
    assert custom.read_text(encoding="utf-8") == ""
    assert soul.read_text(encoding="utf-8") == default_text
    assert legacy.read_text(encoding="utf-8") == "Legacy retrieval procedure"


def test_hermes_rejects_split_instruction_install(tmp_path):
    from memu.hosts.hermes.cli import SPEC

    args = build_host_parser(SPEC).parse_args(["install-instruction", "--skills-dir", str(tmp_path)])
    with pytest.raises(ValueError, match=r"inline in SOUL\.md"):
        instruction._cmd_install_instruction(args)
    assert not list(tmp_path.iterdir())


def test_openclaw_is_a_skill_host() -> None:
    """OpenClaw snapshots skills from ~/.openclaw/skills at session start, so its
    workspace AGENTS.md block must be the pointer, not the full procedure."""
    from memu.hosts.openclaw.cli import SPEC

    assert SPEC.skills_dir == "~/.openclaw/skills"


def test_cola_is_a_skill_host() -> None:
    """Cola loads its user Skills directory, while MEMORY.md carries only the pointer."""
    from memu.hosts.cola.cli import MEMORY_MD, SKILLS_DIR, SPEC

    assert SPEC.instruction_path == MEMORY_MD == "~/.cola/memory-bank/MEMORY.md"
    assert SPEC.skills_dir == SKILLS_DIR == "~/.cola/resources/skills"


def test_workbuddy_defaults_to_soul_as_an_inline_host() -> None:
    args = build_host_parser(WORKBUDDY_SPEC).parse_args(["install-instruction"])

    assert args.path == WORKBUDDY_SOUL_MD
    assert args.legacy_paths == (WORKBUDDY_LEGACY_MEMORY_MD,)
    assert WORKBUDDY_SPEC.skills_dir == ""


def test_default_install_migrates_the_legacy_instruction_after_writing_the_new_target(
    tmp_path: pathlib.Path,
) -> None:
    soul = tmp_path / "SOUL.md"
    memory = tmp_path / "MEMORY.md"
    soul.write_text("# My identity\n", encoding="utf-8")
    memory.write_text("# My memories\n", encoding="utf-8")
    instruction.install(memory, WORKBUDDY_BINARY)
    old_memory = memory.read_text(encoding="utf-8")

    args = _migration_parser(soul, memory).parse_args(["install-instruction"])
    assert instruction._cmd_install_instruction(args) == 0

    soul_text = soul.read_text(encoding="utf-8")
    assert "# My identity" in soul_text
    assert "memu-workbuddy retrieve" in soul_text
    assert soul_text.count(instruction.begin(WORKBUDDY_BINARY)) == 1
    assert memory.read_text(encoding="utf-8") == "# My memories\n"
    assert soul.with_suffix(".md.bak").read_text(encoding="utf-8") == "# My identity\n"
    assert memory.with_suffix(".md.bak").read_text(encoding="utf-8") == old_memory

    before = (soul_text, memory.read_text(encoding="utf-8"))
    assert instruction._cmd_install_instruction(args) == 0
    assert (soul.read_text(encoding="utf-8"), memory.read_text(encoding="utf-8")) == before


def test_default_install_dry_run_reports_but_does_not_migrate(tmp_path: pathlib.Path) -> None:
    soul = tmp_path / "SOUL.md"
    memory = tmp_path / "MEMORY.md"
    memory.write_text("# My memories\n", encoding="utf-8")
    instruction.install(memory, WORKBUDDY_BINARY)
    old_memory = memory.read_text(encoding="utf-8")

    args = _migration_parser(soul, memory).parse_args(["install-instruction", "--dry-run"])
    assert instruction._cmd_install_instruction(args) == 0

    assert not soul.exists()
    assert memory.read_text(encoding="utf-8") == old_memory


def test_default_remove_cleans_current_and_legacy_instruction_paths(tmp_path: pathlib.Path) -> None:
    soul = tmp_path / "SOUL.md"
    memory = tmp_path / "MEMORY.md"
    soul.write_text("# My identity\n", encoding="utf-8")
    memory.write_text("# My memories\n", encoding="utf-8")
    instruction.install(soul, WORKBUDDY_BINARY)
    instruction.install(memory, WORKBUDDY_BINARY)

    args = _migration_parser(soul, memory).parse_args(["remove-instruction"])
    assert instruction._cmd_remove_instruction(args) == 0

    assert soul.read_text(encoding="utf-8") == "# My identity\n"
    assert memory.read_text(encoding="utf-8") == "# My memories\n"


def test_custom_instruction_path_leaves_default_legacy_path_alone(tmp_path: pathlib.Path) -> None:
    soul = tmp_path / "SOUL.md"
    memory = tmp_path / "MEMORY.md"
    custom = tmp_path / "profile" / "SOUL.md"
    instruction.install(memory, WORKBUDDY_BINARY)
    old_memory = memory.read_text(encoding="utf-8")

    args = _migration_parser(soul, memory).parse_args(["install-instruction", "--path", str(custom)])
    assert instruction._cmd_install_instruction(args) == 0

    assert "memu-workbuddy retrieve" in custom.read_text(encoding="utf-8")
    assert memory.read_text(encoding="utf-8") == old_memory


def test_failed_new_target_install_keeps_the_legacy_instruction(monkeypatch, tmp_path: pathlib.Path) -> None:
    soul = tmp_path / "SOUL.md"
    memory = tmp_path / "MEMORY.md"
    instruction.install(memory, WORKBUDDY_BINARY)
    old_memory = memory.read_text(encoding="utf-8")
    args = _migration_parser(soul, memory).parse_args(["install-instruction"])

    install_error = OSError("new target is not writable")

    def fail_install(*_args: object, **_kwargs: object) -> None:
        raise install_error

    monkeypatch.setattr(instruction, "install", fail_install)
    with pytest.raises(OSError, match="not writable"):
        instruction._cmd_install_instruction(args)

    assert memory.read_text(encoding="utf-8") == old_memory


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
    assert "`hits`" in path.read_text(encoding="utf-8")

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
    assert "memu-codex retrieve" in text and "`hits`" in text
    assert not (tmp_path / "skills").exists()


def test_remove_skill_takes_the_whole_directory(tmp_path: pathlib.Path) -> None:
    skills = tmp_path / "skills"
    instruction.install_skill(skills, BINARY)
    assert (skills / instruction.SKILL_NAME / "SKILL.md").is_file()

    changed, diff = instruction.remove_skill(skills, BINARY)

    assert changed and diff
    assert not (skills / instruction.SKILL_NAME).exists(), "the skill directory goes whole, as it arrived"


def test_remove_skill_absent_is_a_noop(tmp_path: pathlib.Path) -> None:
    assert instruction.remove_skill(tmp_path / "skills", BINARY) == (False, "")


def test_remove_skill_leaves_a_foreign_same_named_directory_alone(tmp_path: pathlib.Path) -> None:
    """A memu-retrieve dir without our SKILL.md is not ours to take back."""
    foreign = tmp_path / "skills" / instruction.SKILL_NAME
    foreign.mkdir(parents=True)
    (foreign / "notes.md").write_text("the user's own\n", encoding="utf-8")

    with pytest.raises(ValueError, match="preserved"):
        instruction.remove_skill(tmp_path / "skills", BINARY)
    assert (foreign / "notes.md").is_file()


def test_remove_skill_dry_run_writes_nothing(tmp_path: pathlib.Path) -> None:
    skills = tmp_path / "skills"
    instruction.install_skill(skills, BINARY)

    changed, diff = instruction.remove_skill(skills, BINARY, dry_run=True)

    assert not changed
    assert diff, "a dry run still reports what it would do"
    assert (skills / instruction.SKILL_NAME / "SKILL.md").is_file()


def test_cli_remove_takes_the_skill_with_the_instruction_for_a_skill_host(tmp_path: pathlib.Path) -> None:
    agents = tmp_path / "AGENTS.md"
    skills = tmp_path / "skills"
    install = build_parser().parse_args(["install-instruction", "--path", str(agents), "--skills-dir", str(skills)])
    assert instruction._cmd_install_instruction(install) == 0
    assert (skills / instruction.SKILL_NAME / "SKILL.md").is_file()

    remove = build_parser().parse_args(["remove-instruction", "--path", str(agents), "--skills-dir", str(skills)])
    assert instruction._cmd_remove_instruction(remove) == 0

    assert not (skills / instruction.SKILL_NAME).exists(), "the pointed-at skill leaves with its pointer"
    assert instruction.begin(BINARY) not in agents.read_text(encoding="utf-8")


def test_cli_remove_dry_run_leaves_the_skill_in_place(tmp_path: pathlib.Path) -> None:
    agents = tmp_path / "AGENTS.md"
    skills = tmp_path / "skills"
    install = build_parser().parse_args(["install-instruction", "--path", str(agents), "--skills-dir", str(skills)])
    assert instruction._cmd_install_instruction(install) == 0

    remove = build_parser().parse_args([
        "remove-instruction",
        "--path",
        str(agents),
        "--skills-dir",
        str(skills),
        "--dry-run",
    ])
    assert instruction._cmd_remove_instruction(remove) == 0

    assert (skills / instruction.SKILL_NAME / "SKILL.md").is_file()
    assert instruction.begin(BINARY) in agents.read_text(encoding="utf-8")


def test_cli_remove_without_a_skills_dir_touches_no_skill(tmp_path: pathlib.Path) -> None:
    """An inline host passes an empty --skills-dir and must not error on the skill step."""
    agents = tmp_path / "AGENTS.md"
    instruction.install(agents, BINARY)

    remove = build_parser().parse_args(["remove-instruction", "--path", str(agents), "--skills-dir", ""])
    assert instruction._cmd_remove_instruction(remove) == 0
    assert instruction.begin(BINARY) not in agents.read_text(encoding="utf-8")


@pytest.mark.parametrize("host", ["hermes", "pi", "codex", "claude_code"])
def test_host_cli_removes_all_owned_blocks_and_legacy_skill(tmp_path, monkeypatch, host):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes"))
    script = textwrap.dedent("""\
        import importlib
        import sys
        from pathlib import Path
        from unittest.mock import patch
        from memu.hosts import instruction, templates
        from memu.hosts.host_cli import build_parser

        cli = importlib.import_module(f'memu.hosts.{sys.argv[1]}.cli')
        spec = cli.SPEC
        args = build_parser(spec).parse_args(['remove-instruction'])
        path = Path(args.path).expanduser()
        skills = Path(args.skills_dir).expanduser()
        assert args.skills_dir
        assert path.is_relative_to(Path(sys.argv[2]))
        assert skills.is_relative_to(Path(sys.argv[2]))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# User rules\\n', encoding='utf-8')
        with patch.object(templates, 'fetch', return_value=None):
            assert cli.main(['install-instruction']) == 0
            assert cli.main(['install-instruction']) == 0
        text = path.read_text(encoding='utf-8')
        assert text.count(instruction.begin(spec.binary)) == 1
        legacy = f'{instruction.begin(spec.binary)}\\nOld version body.\\n{instruction.END}\\n'
        other = instruction.block('memu-other')
        unowned = '<!-- memu:begin -->\\nKeep unknown markers.\\n<!-- memu:end -->\\n'
        path.write_text(text + legacy + other + unowned, encoding='utf-8')
        instruction.install_skill(skills, spec.binary)
        before = path.read_bytes()
        assert cli.main(['remove-instruction', '--dry-run']) == 0
        assert path.read_bytes() == before
        assert instruction.skill_path(skills).is_file()
        assert cli.main(['remove-instruction']) == 0
        result = path.read_text(encoding='utf-8')
        assert instruction.begin(spec.binary) not in result
        assert '# User rules' in result and other in result and unowned in result
        assert not instruction.skill_path(skills).exists()
        assert cli.main(['remove-instruction']) == 0
        assert path.read_text(encoding='utf-8') == result
        """)
    subprocess.run([sys.executable, "-c", script, host, str(tmp_path)], check=True, timeout=30)  # noqa: S603
