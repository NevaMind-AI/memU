from __future__ import annotations

import json
from importlib.resources import files

import pytest

from memu import config_file
from memu.hosts import installation, templates
from memu.hosts.pi import hook_install, install
from memu.hosts.pi.cli import main


@pytest.fixture
def machine(tmp_path, monkeypatch):
    home = tmp_path / "agent"
    home.mkdir()
    base = tmp_path / "state"
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(home))
    monkeypatch.setattr(install.shutil, "which", lambda _: "pi")
    monkeypatch.setattr(config_file, "read", lambda: {"MEMU_MEMORY_MODE": "cloud", "MEMU_CLOUD_API_KEY": "test"})
    monkeypatch.setattr(installation.events, "record", lambda *a, **k: None)
    calls = []

    async def command(argv):
        calls.append(argv)
        return 0

    monkeypatch.setattr(install, "_command", command)
    return home, base, calls


def invoke(machine, *args):
    return main(["install", "--non-interactive", "--base-dir", str(machine[1]), *args])


def test_install_is_idempotent_and_preserves_pi_configuration(machine, capsys):
    home, base, calls = machine
    settings = home / "settings.json"
    auth = home / "auth.json"
    settings.write_text('{"defaultModel":"luna"}', encoding="utf-8")
    auth.write_text('{"private":"preserved"}', encoding="utf-8")
    foreign = home / "extensions/other.ts"
    foreign.parent.mkdir()
    foreign.write_text("// another extension", encoding="utf-8")
    base.mkdir()
    cursor = base / "cursor.json"
    cursor.write_text("preserved", encoding="utf-8")
    before = {p: p.read_bytes() for p in (settings, auth, foreign, cursor)}
    assert invoke(machine, "--json") == 0
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [row["stage"] for row in rows if row["status"] == "passed"] == [1, 2, 3]
    assert all(row["total_stages"] == 3 for row in rows)
    assert rows[-1]["complete"] is True
    assert rows[-1]["hook_verification"] == "local_extension_readback"
    assert "/reload" in rows[-1]["notice"]
    destination = home / "extensions/memu-retrieval.ts"
    original = destination.read_bytes()
    assert invoke(machine, "--json") == 0
    assert destination.read_bytes() == original
    assert all(p.read_bytes() == content for p, content in before.items())
    assert calls == [["doctor", "--backend-only"], ["doctor", "--backend-only"]]


@pytest.mark.parametrize("condition", ["missing-pi", "foreign-file", "edited-skill", "backend"])
def test_install_stops_before_hook_mutation(machine, monkeypatch, capsys, condition):
    home, _, calls = machine
    target = home / "extensions/memu-retrieval.ts"
    if condition == "missing-pi":
        monkeypatch.setattr(install.shutil, "which", lambda _: None)
    elif condition == "foreign-file":
        target.parent.mkdir()
        target.write_text("// user file", encoding="utf-8")
    elif condition == "edited-skill":
        skill = home / "skills/memu-retrieve/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("user data", encoding="utf-8")
    else:

        async def failed(argv):
            return 1

        monkeypatch.setattr(install, "_command", failed)
    assert invoke(machine, "--json") == 2
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert rows[-1]["complete"] is False
    assert rows[-1]["status"] == "blocked"
    if condition == "foreign-file":
        assert target.read_text(encoding="utf-8") == "// user file"
    else:
        assert not target.exists()
    if condition != "backend":
        assert not calls


@pytest.mark.parametrize("language,heading", [("en", "Welcome to memU"), ("zh", "欢迎安装 memU")])
def test_install_has_three_stage_localized_progress(machine, capsys, language, heading):
    assert invoke(machine, "--language", language) == 0
    text = capsys.readouterr().out
    assert heading in text
    assert "3/3" in text
    assert "/5" not in text


def test_readback_failure_is_not_reported_as_complete(machine, monkeypatch, capsys):
    home, _, _ = machine
    path = home / "extensions/memu-retrieval.ts"
    path.parent.mkdir()
    path.write_text("not the expected content", encoding="utf-8")
    monkeypatch.setattr(install, "_check_files", lambda: None)
    monkeypatch.setattr(hook_install, "install", lambda _: path)
    assert invoke(machine, "--json") == 1
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert rows[-1]["complete"] is False
    assert rows[-1]["status"] == "failed"


@pytest.mark.parametrize("filename", ["INSTALL.md", "UNINSTALL.md"])
def test_pi_guides_use_the_installed_extension_contract(tmp_path, monkeypatch, filename):
    embedded = (files("memu.hosts.pi") / filename).read_text(encoding="utf-8")
    assert templates._valid_host_doc("pi", filename, embedded)
    old = " ".join("{{" + name + "}}" for name in templates.DOC_REQUIRED_TOKENS)
    monkeypatch.setenv("MEMU_DOCS_BASE_URL", "https://example.invalid")
    monkeypatch.setattr(templates, "_get", lambda _: old)
    monkeypatch.setattr(templates, "_docs_cache_dir", lambda _: tmp_path)
    (tmp_path / filename).write_text(old, encoding="utf-8")
    assert templates.resolve_doc("pi", filename, embedded) == embedded
