"""Direct host cleanup must establish ownership before changing either artifact."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from memu.hosts import installation, instruction
from memu.hosts.claude_code.cli import main as claude_main
from memu.hosts.codex.cli import main as codex_main


@pytest.fixture(params=[("memu-codex", codex_main), ("memu-claude-code", claude_main)])
def host(request: pytest.FixtureRequest) -> Any:
    return request.param


def setup_files(tmp_path: Path, binary: str) -> tuple[Path, Path]:
    rules = tmp_path / "rules.md"
    rules.write_text("User rules.\n\n" + instruction.block(binary, skill=True), encoding="utf-8")
    skill = tmp_path / "skills" / instruction.SKILL_NAME / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(instruction.skill_document(binary), encoding="utf-8")
    return rules, skill


@pytest.mark.parametrize("change", ["edited", "extra-file", "extra-directory", "missing-marker", "marker-directory"])
@pytest.mark.parametrize("dry_run", [False, True])
def test_cli_refuses_unowned_skill_before_removing_its_pointer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    host: Any,
    change: str,
    dry_run: bool,
) -> None:
    binary, main = host
    monkeypatch.setattr("memu.events.flush", lambda: None)
    rules, skill = setup_files(tmp_path, binary)
    if change == "edited":
        skill.write_text("User-authored skill.\n", encoding="utf-8")
    elif change == "extra-file":
        (skill.parent / "notes.txt").write_text("User notes.\n", encoding="utf-8")
    elif change == "extra-directory":
        (skill.parent / "user-data").mkdir()
        (skill.parent / "user-data/notes.txt").write_text("Nested notes.\n", encoding="utf-8")
    elif change == "marker-directory":
        skill.unlink()
        skill.mkdir()
    else:
        skill.unlink()
        (skill.parent / "notes.txt").write_text("Foreign directory.\n", encoding="utf-8")
    before = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    entries_before = {path.relative_to(tmp_path) for path in tmp_path.rglob("*")}
    argv = ["remove-instruction", "--path", str(rules), "--skills-dir", str(skill.parent.parent)]
    assert main([*argv, *(["--dry-run"] if dry_run else [])]) != 0
    output = capsys.readouterr()
    assert "skill" in output.err.lower()
    assert "preserv" in output.err.lower()
    assert {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before
    assert {path.relative_to(tmp_path) for path in tmp_path.rglob("*")} == entries_before


def test_cli_removes_owned_skill_and_block_without_affecting_other_data(tmp_path: Path, host: Any) -> None:
    binary, main = host
    rules, skill = setup_files(tmp_path, binary)
    other = skill.parent.parent / "another-skill"
    other.mkdir()
    (other / "SKILL.md").write_text("Other integration.\n", encoding="utf-8")
    memory = tmp_path / "memory.sqlite3"
    memory.write_bytes(b"fixture: do not touch")
    argv = ["remove-instruction", "--path", str(rules), "--skills-dir", str(skill.parent.parent)]
    assert main([*argv, "--dry-run"]) == 0
    assert skill.exists() and instruction.begin(binary) in rules.read_text(encoding="utf-8")
    assert not rules.with_suffix(".md.bak").exists()
    assert main(argv) == 0
    assert not skill.parent.exists()
    assert rules.read_text(encoding="utf-8") == "User rules.\n"
    assert main(argv) == 0
    assert memory.read_bytes() == b"fixture: do not touch"
    assert (other / "SKILL.md").read_text(encoding="utf-8") == "Other integration.\n"


def link_or_skip(target: Path, link: Path, *, directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError as error:
        if sys.platform == "win32" and getattr(error, "winerror", None) == 1314:
            pytest.skip("Windows file/directory symlinks require Developer Mode or privilege")
        raise


@pytest.mark.parametrize("link_kind", ["skill", "dangling-skill", "directory", "dangling-directory", "skills-root"])
def test_cli_preserves_links_and_their_targets_before_changing_instructions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    host: Any,
    link_kind: str,
) -> None:
    binary, main = host
    monkeypatch.setattr("memu.events.flush", lambda: None)
    rules, skill = setup_files(tmp_path, binary)
    original = rules.read_bytes()
    outside = tmp_path / "outside"
    outside.mkdir()
    if link_kind in {"skill", "dangling-skill"}:
        skill.unlink()
        target = outside / "SKILL.md"
        if link_kind == "skill":
            target.write_text(instruction.skill_document(binary), encoding="utf-8")
        link_or_skip(target, skill)
        link = skill
    elif link_kind in {"directory", "dangling-directory"}:
        skill.unlink()
        skill.parent.rmdir()
        target = outside / "owned-looking"
        if link_kind == "directory":
            target.mkdir()
            (target / "SKILL.md").write_text(instruction.skill_document(binary), encoding="utf-8")
        link_or_skip(target, skill.parent, directory=True)
        link = skill.parent
    else:
        skill.unlink()
        skill.parent.rmdir()
        skill.parent.parent.rmdir()
        (outside / instruction.SKILL_NAME).mkdir()
        (outside / instruction.SKILL_NAME / "SKILL.md").write_text(instruction.skill_document(binary), encoding="utf-8")
        link_or_skip(outside, skill.parent.parent, directory=True)
        link = skill.parent.parent
    outside_before = {path.relative_to(outside): path.read_bytes() for path in outside.rglob("*") if path.is_file()}
    argv = ["remove-instruction", "--path", str(rules), "--skills-dir", str(skill.parent.parent)]
    assert main(argv) != 0
    assert rules.read_bytes() == original
    assert link.is_symlink()
    assert {
        path.relative_to(outside): path.read_bytes() for path in outside.rglob("*") if path.is_file()
    } == outside_before
    assert not rules.with_suffix(".md.bak").exists()


@pytest.mark.parametrize("binary", ["memu-codex", "memu-claude-code"])
def test_installer_ownership_gate_preserves_the_existing_migration_contract(tmp_path: Path, binary: str) -> None:
    rules, skill = setup_files(tmp_path, binary)
    instruction_name = "AGENTS.md" if binary == "memu-codex" else "CLAUDE.md"
    rules.rename(tmp_path / instruction_name)
    installation.check_cleanup(tmp_path, binary, instruction_name)
    (skill.parent / "notes.txt").write_text("Keep.\n", encoding="utf-8")
    with pytest.raises(installation.Blocked):
        installation.check_cleanup(tmp_path, binary, instruction_name)
    assert (skill.parent / "notes.txt").read_text(encoding="utf-8") == "Keep.\n"


def test_direct_skill_removal_also_checks_ownership(tmp_path: Path) -> None:
    _, skill = setup_files(tmp_path, "memu-codex")
    skill.write_text("User content.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="preserved"):
        instruction.remove_skill(skill.parent.parent, "memu-codex")
    assert skill.read_text(encoding="utf-8") == "User content.\n"


def test_unreadable_skill_directory_does_not_look_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    host: Any,
) -> None:
    binary, main = host
    monkeypatch.setattr("memu.events.flush", lambda: None)
    rules, skill = setup_files(tmp_path, binary)
    before = rules.read_bytes()
    original = Path.lstat

    def lstat(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path == skill.parent:
            raise PermissionError("fixture permission denied")  # noqa: TRY003
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", lstat)
    assert main(["remove-instruction", "--path", str(rules), "--skills-dir", str(skill.parent.parent)]) != 0
    assert rules.read_bytes() == before
    assert skill.read_text(encoding="utf-8") == instruction.skill_document(binary)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows directory junctions")
@pytest.mark.parametrize("junction_kind", ["skill-directory", "skills-root"])
def test_windows_directory_junctions_preserve_external_skill_and_instructions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    host: Any,
    junction_kind: str,
) -> None:
    binary, main = host
    monkeypatch.setattr("memu.events.flush", lambda: None)
    rules, skill = setup_files(tmp_path, binary)
    before = rules.read_bytes()
    skill.unlink()
    skill.parent.rmdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    if junction_kind == "skill-directory":
        link = skill.parent
        target = outside
        external_skill = target / "SKILL.md"
    else:
        skill.parent.parent.rmdir()
        link = skill.parent.parent
        target = outside
        (target / instruction.SKILL_NAME).mkdir()
        external_skill = target / instruction.SKILL_NAME / "SKILL.md"
    external_skill.write_text(instruction.skill_document(binary), encoding="utf-8")
    result = subprocess.run(  # noqa: S603 -- both paths are isolated pytest temporary fixtures
        [str(Path(os.environ["SYSTEMROOT"]) / "System32/cmd.exe"), "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    try:
        assert main(["remove-instruction", "--path", str(rules), "--skills-dir", str(skill.parent.parent)]) != 0
        assert rules.read_bytes() == before
        assert external_skill.read_text(encoding="utf-8") == instruction.skill_document(binary)
        assert link.exists()
    finally:
        # Removing a junction itself preserves the target directory.
        if link.exists():
            link.rmdir()
