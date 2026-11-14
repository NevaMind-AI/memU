"""Hermes installation patches SOUL.md and uses only CLI-based legacy cleanup."""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
from typing import Any

import pytest

from memu import config_file
from memu.hosts import installation, instruction, templates
from memu.hosts.hermes import hook_install, install
from memu.hosts.hermes.cli import main


def test_adapter_has_no_host_python_imports():
    import ast
    from importlib.resources import files

    forbidden = {"hermes_constants", "hermes_cli", "hermes_bootstrap", "agent", "pm"}
    for path in files("memu.hosts.hermes").iterdir():
        if not path.name.endswith(".py"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not any(alias.name.split(".")[0] in forbidden for alias in node.names), path.name
            elif isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in forbidden, path.name


@pytest.fixture
def machine(tmp_path, monkeypatch):
    home, base = tmp_path / "hermes", tmp_path / "state"
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(install.shutil, "which", lambda _: "hermes")
    monkeypatch.setattr(install.platform, "system", lambda: "Windows")
    monkeypatch.setattr(config_file, "read", lambda: {"MEMU_MEMORY_MODE": "cloud", "MEMU_CLOUD_API_KEY": "test"})
    monkeypatch.setattr(installation.events, "record", lambda *a, **k: None)
    calls = []
    dispatch = install._command

    async def command(argv):
        calls.append(argv)
        if argv[0] in {"doctor", "schedule"}:
            return 0
        return await dispatch(argv)

    hook_config: dict[str, Any] = {}

    def hermes_command(*argv):
        if argv == ("config", "get", "hooks", "--json"):
            return json.dumps(hook_config)
        if argv[:3] == ("config", "set", "hooks.on_session_end"):
            hook_config["on_session_end"] = json.loads(argv[3])
            return ""
        if argv == ("config", "unset", "hooks.on_session_end"):
            hook_config.pop("on_session_end", None)
            return ""
        if argv == ("hooks", "list"):
            return "\n".join(entry["command"] for entry in hook_config.get("on_session_end", []))
        calls.append(list(argv))
        assert argv == ("plugins", "remove", hook_install.NAME)
        shutil.rmtree(hook_install.target())
        return ""

    monkeypatch.setattr(install, "_command", command)
    monkeypatch.setattr(hook_install, "command", hermes_command)
    return home, base, calls


def legacy_plugin(home):
    path = home / "plugins" / hook_install.NAME
    path.mkdir(parents=True)
    for name in ("plugin.yaml", "__init__.py"):
        (path / name).write_text(hook_install.MARKER + "\nlegacy content", encoding="utf-8")
    return path


def test_install_and_uninstall_patch_only_owned_content(machine, capsys):
    home, base, calls = machine
    home.mkdir()
    soul = home / "SOUL.md"
    soul.write_text("User identity\n", encoding="utf-8")
    settings = home / "config.yaml"
    settings.write_text("model: user-model\n", encoding="utf-8")
    for _ in range(2):
        assert main(["install", "--non-interactive", "--json", "--base-dir", str(base)]) == 0
        result = json.loads(capsys.readouterr().out.splitlines()[-1])
        assert result["complete"] is True
        assert result["instruction_verification"] == "soul_managed_block_readback"
        assert result["instruction_path"] == str(soul)
        assert result["restart_required"] is True
        assert "gateway_reload" not in result
        text = soul.read_text(encoding="utf-8")
        assert text.count(instruction.begin("memu-hermes")) == 1
        assert "retrieve relevant memory on demand" in text
        assert not (home / "skills" / "memu-retrieve").exists()
        assert not (home / "plugins").exists()
    assert (
        calls
        == [
            ["doctor", "--backend-only"],
            ["schedule", "uninstall", "--base-dir", str(base)],
            ["install-instruction"],
        ]
        * 2
    )
    for _ in range(2):
        assert main(["uninstall", "--json", "--base-dir", str(base)]) == 0
        assert json.loads(capsys.readouterr().out)["status"] == "passed"
    assert soul.read_text(encoding="utf-8") == "User identity\n"
    assert settings.read_text(encoding="utf-8") == "model: user-model\n"
    assert base.exists()


@pytest.mark.parametrize("operation", ["install", "uninstall"])
def test_migrate_legacy_plugin_and_skill(machine, capsys, operation):
    home, base, calls = machine
    path = legacy_plugin(home)
    skill = instruction.skill_path(home / "skills")
    skill.parent.mkdir(parents=True)
    skill.write_text(instruction.skill_document("memu-hermes"), encoding="utf-8")
    argv = [operation, "--json", "--base-dir", str(base)]
    if operation == "install":
        argv += ["--non-interactive"]
    assert main(argv) == 0
    capsys.readouterr()
    assert ["plugins", "remove", hook_install.NAME] in calls
    assert not path.exists()
    assert not skill.exists()
    assert (home / "SOUL.md").exists() is (operation == "install")


@pytest.mark.parametrize("failure", ["foreign", "extra", "removal", "readback"])
def test_legacy_cleanup_failure_preserves_instructions(machine, monkeypatch, failure):
    home, base, _ = machine
    path = legacy_plugin(home)
    soul = home / "SOUL.md"
    soul.write_text("User identity\n", encoding="utf-8")
    if failure == "foreign":
        (path / "__init__.py").write_text("User plugin", encoding="utf-8")
    elif failure == "extra":
        (path / "notes.txt").write_text("User notes", encoding="utf-8")
    elif failure == "removal":

        def fail(*argv):
            raise RuntimeError("CLI removal failed")  # noqa: TRY003

        monkeypatch.setattr(hook_install, "command", fail)
    else:
        monkeypatch.setattr(hook_install, "command", lambda *argv: "")
    assert main(["install", "--non-interactive", "--json", "--base-dir", str(base)]) == 1
    assert soul.read_text(encoding="utf-8") == "User identity\n"
    assert path.exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [0, 1])
async def test_backend_dispatch(monkeypatch, status):
    from memu.hosts import host_cli

    async def backend(spec, args):
        assert spec.host == "hermes" and args.backend_only is True
        return status

    monkeypatch.setattr(host_cli, "_cmd_backend_doctor", backend)
    assert await install._command(["doctor", "--backend-only"]) == status


def test_missing_hermes_stops_install(machine, monkeypatch, capsys):
    home, base, _ = machine
    monkeypatch.setattr(install.shutil, "which", lambda _: None)
    assert main(["install", "--non-interactive", "--json", "--base-dir", str(base)]) == 2
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["complete"] is False
    assert not (home / "SOUL.md").exists()


def test_unrecognized_shell_hook_stops_legacy_migration(machine, monkeypatch, capsys):
    home, base, calls = machine
    path = legacy_plugin(home)
    original = hook_install.command

    def command(*argv):
        return "No shell hooks" if argv == ("hooks", "list") else original(*argv)

    monkeypatch.setattr(hook_install, "command", command)
    assert main(["install", "--non-interactive", "--json", "--base-dir", str(base)]) == 1
    assert path.exists()
    assert not (home / "SOUL.md").exists()
    assert ["plugins", "remove", hook_install.NAME] not in calls
    assert not any(call[0] == "schedule" for call in calls)
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["complete"] is False


def test_readback_must_match(machine, monkeypatch):
    home, base, _ = machine
    home.mkdir()
    (home / "SOUL.md").write_text("Unchanged", encoding="utf-8")

    async def command(argv):
        return 0

    monkeypatch.setattr(install, "_command", command)
    with pytest.raises(installation.Failed, match="readback"):
        asyncio.run(install._stage(3, argparse.Namespace(base_dir=base)))


@pytest.mark.parametrize("doc", ["INSTALL.md", "UNINSTALL.md"])
@pytest.mark.parametrize("marker", ["", "<!-- memu-hermes-install: plugin-v2 -->"])
def test_guides_reject_older_install_docs(marker, doc):
    tokens = (
        "<!-- {{task_name}} | {{former_task_names}} | {{all_task_names}} -->\n<!-- memu-cleanup: owned-artifacts -->"
    )
    assert not templates._valid_host_doc("hermes", doc, marker + "\n" + tokens)
    assert templates._valid_host_doc("hermes", doc, "<!-- memu-hermes-install: soul-v1 -->\n" + tokens)
