"""Cleanup follows recorded artifacts rather than template/package version pairs."""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable
from importlib.resources import files
from pathlib import Path

import pytest

from memu.hosts import instruction, templates
from memu.hosts.claude_code.cli import main as claude_main
from memu.hosts.codex.cli import main as codex_main
from memu.hosts.pi.cli import main as pi_main


@pytest.mark.parametrize(
    "binary", ["memu-codex", "memu-claude-code", "memu-pi", "memu-hermes", "memu-openclaw", "memu-cola"]
)
def test_recorded_server_skill_survives_package_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, binary: str
) -> None:
    skills = tmp_path / "skills"
    rules = tmp_path / "AGENTS.md"
    instruction.install_skill(skills, binary, skill_text="Remote procedure: {binary} retrieve.\n")
    instruction.install(rules, binary, skill=True)
    monkeypatch.setattr(instruction, "SKILL_TEMPLATE", "An unrelated future template.\n")
    assert instruction.cleanup([rules], binary, skills_dir=skills, dry_run=True)
    assert instruction.skill_path(skills).exists()
    assert instruction.cleanup([rules], binary, skills_dir=skills)
    assert not instruction.skill_path(skills).parent.exists()
    assert rules.read_text(encoding="utf-8") == ""
    assert instruction.cleanup([rules], binary, skills_dir=skills) == []


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("refresh", [False, True])
def test_template_line_endings_match_the_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, newline: str, refresh: bool
) -> None:
    skills = tmp_path / "skills"
    remote = f"Remote {{binary}} retrieve.{newline}Second line.{newline}"
    if refresh:
        instruction.install_skill(skills, "memu-openclaw")
        monkeypatch.setattr(instruction.templates, "fetch", lambda _: remote)
        instruction.refresh(tmp_path / "AGENTS.md", "memu-openclaw", skills_dir=skills)
    else:
        instruction.install_skill(skills, "memu-openclaw", skill_text=remote)
    target = instruction.skill_path(skills)
    installed = target.read_text(encoding="utf-8")
    assert installed == "Remote memu-openclaw retrieve.\nSecond line.\n"
    assert instruction.check_skill_cleanup(skills, "memu-openclaw")
    target.write_text(installed + "User edit.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="ownership record"):
        instruction.remove_skill(skills, "memu-openclaw")
    target.write_text(installed, encoding="utf-8")
    assert instruction.remove_skill(skills, "memu-openclaw")[0]


def test_refresh_updates_the_ownership_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    skills = tmp_path / "skills"
    instruction.install_skill(skills, "memu-codex")
    monkeypatch.setattr(instruction.templates, "fetch", lambda _: "New remote procedure: {binary} retrieve.\n")
    assert instruction.refresh(tmp_path / "AGENTS.md", "memu-codex", skills_dir=skills)
    assert instruction.remove_skill(skills, "memu-codex")[0]


@pytest.mark.parametrize("change", ["edited", "wrong-host", "invalid-record", "extra-entry"])
def test_recorded_skill_still_protects_user_changes(tmp_path: Path, change: str) -> None:
    skills = tmp_path / "skills"
    rules = tmp_path / "AGENTS.md"
    instruction.install_skill(skills, "memu-codex")
    instruction.install(rules, "memu-codex", skill=True)
    target = instruction.skill_path(skills)
    record = target.with_name(".memu-owned.json")
    binary = "memu-codex"
    if change == "edited":
        target.write_text("User edits.\n", encoding="utf-8")
    elif change == "wrong-host":
        binary = "memu-claude-code"
    elif change == "invalid-record":
        record.write_text("broken", encoding="utf-8")
    else:
        (target.parent / "notes.txt").write_text("Keep.\n", encoding="utf-8")
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    with pytest.raises(ValueError):
        instruction.cleanup([rules], binary, skills_dir=skills)
    assert {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before


@pytest.mark.parametrize(
    "name,main,rules_name",
    [("codex", codex_main, "AGENTS.md"), ("claude", claude_main, "CLAUDE.md"), ("pi/agent", pi_main, "AGENTS.md")],
)
@pytest.mark.parametrize("edited", [False, True])
def test_uninstall_inspects_legacy_retrieval_even_without_current_hooks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    main: Callable[[list[str] | None], int],
    rules_name: str,
    edited: bool,
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(tmp_path / ".pi/agent"))
    home = tmp_path / f".{name}"
    binary = {"codex": "memu-codex", "claude": "memu-claude-code", "pi/agent": "memu-pi"}[name]
    rules = home / rules_name
    instruction.install(rules, binary, skill=True)
    rules.write_text("User rules.\n\n" + rules.read_text(encoding="utf-8"), encoding="utf-8")
    instruction.install_skill(home / "skills", binary, skill_text="Remote: {binary} retrieve.\n")
    if name == "pi/agent":
        instruction.install(home / "AGENTS.override.md", binary, skill=True)
    skill = instruction.skill_path(home / "skills")
    if edited:
        skill.write_text("User edits.\n", encoding="utf-8")
    before = rules.read_bytes()
    assert main(["uninstall"]) == int(edited)
    if edited:
        assert rules.read_bytes() == before
        assert skill.read_text(encoding="utf-8") == "User edits.\n"
    else:
        assert rules.read_text(encoding="utf-8") == "User rules.\n"
        assert not skill.parent.exists()
        if name == "pi/agent":
            assert not (home / "AGENTS.override.md").read_text(encoding="utf-8").strip()
        assert main(["uninstall"]) == 0


def test_linked_receipt_is_preserved_before_install_or_cleanup(tmp_path: Path) -> None:
    instruction.install_skill(tmp_path, "memu-codex")
    target = instruction.skill_path(tmp_path)
    receipt = target.with_name(".memu-owned.json")
    external = tmp_path / "user-record.json"
    external.write_bytes(receipt.read_bytes())
    receipt.unlink()
    try:
        receipt.symlink_to(external)
    except OSError as error:
        if getattr(error, "winerror", None) == 1314:
            pytest.skip("Windows symlinks require Developer Mode or privilege")
        raise
    before = target.read_bytes(), external.read_bytes()
    with pytest.raises(ValueError):
        instruction.remove_skill(tmp_path, "memu-codex")
    with pytest.raises(ValueError):
        instruction.install_skill(tmp_path, "memu-codex", skill_text="Changed remote content")
    assert (target.read_bytes(), external.read_bytes()) == before
    assert receipt.is_symlink()


def test_receipt_allows_future_optional_fields(tmp_path: Path) -> None:
    instruction.install_skill(tmp_path, "memu-codex")
    record_path = instruction.skill_path(tmp_path).with_name(".memu-owned.json")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["future_metadata"] = {"source": "remote"}
    record_path.write_text(json.dumps(record), encoding="utf-8")
    assert instruction.remove_skill(tmp_path, "memu-codex")[0]


@pytest.mark.parametrize(
    "host", ["codex", "claude_code", "pi", "hermes", "openclaw", "cola", "workbuddy", "cursor", "generic"]
)
def test_remote_uninstall_guides_need_the_cleanup_capability(host: str) -> None:
    spec = importlib.import_module(f"memu.hosts.{host}.cli").SPEC
    embedded = files(spec.package).joinpath("UNINSTALL.md").read_text(encoding="utf-8")
    assert templates._valid_host_doc(spec.host, "UNINSTALL.md", embedded)
    assert not templates._valid_host_doc(
        spec.host, "UNINSTALL.md", embedded.replace("<!-- memu-cleanup: owned-artifacts -->", "")
    )
