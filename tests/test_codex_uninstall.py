import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from memu.hosts.codex import uninstall
from memu.hosts.codex.cli import main


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    root = tmp_path / ".codex"
    root.mkdir()
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "another-home"))
    return root


@pytest.mark.parametrize("trust_failure", [False, True])
def test_uninstall_removes_both_handlers_and_preserves_foreign_trust(home, monkeypatch, trust_failure):  # noqa: C901
    path = home / "hooks.json"
    foreign = {"type": "command", "command": "foreign-hook"}
    untrusted = {"type": "command", "command": "untrusted-hook"}
    compound = {"type": "command", "command": "memu-codex memorize-hook --agent codex && other-command"}
    original: dict[str, Any] = {
        "custom": "kept",
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "*",
                    "hooks": [
                        {"type": "command", "command": "memu-codex prompt-hook --default-home"},
                        foreign,
                        {"type": "command", "command": "memu-codex memorize-hook --agent codex --default-home"},
                        untrusted,
                        {"type": "command", "command": "memu-codex prompt-hook"},
                        compound,
                    ],
                },
                {"hooks": [foreign.copy()]},
            ],
            "Stop": [{"hooks": [{"type": "command", "command": "other-stop"}]}],
        },
    }
    path.write_text(json.dumps(original), encoding="utf-8")
    original_bytes = path.read_bytes()
    retained = {
        "config.toml": 'model = "user-model"\n',
        "AGENTS.md": "user instructions",
        "skills/memu-retrieve/SKILL.md": "legacy skill",
        "automations/legacy/automation.toml": "legacy task",
        "../.memu/hosts/codex/.session_manifest.codex.json.pending": "pending cursor",
        "../.memu/hosts/codex/.self_sessions.codex.json": "self sessions",
        "../.memu/hosts/codex/results/recoverable.json": "pending result",
    }
    for name, content in retained.items():
        target = home / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    calls = []
    trusted = {}

    class Server:
        def __init__(self, executable, cwd, codex_home):
            assert codex_home == home
            assert executable == "fixture-codex"
            for entry in self.entries():
                if entry["command"] == "foreign-hook":
                    trusted[entry["key"]] = entry["currentHash"]

        def entries(self):
            config = json.loads(path.read_text())
            return [
                {
                    "command": hook["command"],
                    "sourcePath": str(path),
                    "key": f"{i}:{j}",
                    "currentHash": hashlib.sha256(json.dumps(hook, sort_keys=True).encode()).hexdigest(),
                }
                for i, group in enumerate(config["hooks"]["UserPromptSubmit"])
                for j, hook in enumerate(group["hooks"])
            ]

        def request(self, method, params=None):
            calls.append(method)
            if method == "config/value/write":
                if trust_failure:
                    raise RuntimeError("Trust update failed")  # noqa: TRY003
                key = json.loads(params["keyPath"].removeprefix("hooks.state.").removesuffix(".trusted_hash"))
                trusted[key] = params["value"]
            if method != "hooks/list":
                return {}
            entries = self.entries()
            for entry in entries:
                entry["trustStatus"] = "trusted" if trusted.get(entry["key"]) == entry["currentHash"] else "untrusted"
            return {"data": [{"hooks": entries}]}

        def notify(self, method):
            pass

        def close(self):
            pass

    monkeypatch.setattr(
        uninstall.cli_prepare, "prepare", lambda codex: {"status": "passed", "executable": "fixture-codex"}
    )
    monkeypatch.setattr(uninstall.hooks, "AppServer", Server)
    assert main(["uninstall"]) == (1 if trust_failure else 0)
    result = json.loads(path.read_text())
    if trust_failure:
        assert not any(
            uninstall._owned(hook) for group in result["hooks"]["UserPromptSubmit"] for hook in group["hooks"]
        )
        assert (home / "hooks.json.memu-uninstall-backup").read_bytes() == original_bytes
        return
    assert result["custom"] == "kept"
    assert result["hooks"]["Stop"] == original["hooks"]["Stop"]
    assert result["hooks"]["UserPromptSubmit"] == [
        {"matcher": "*", "hooks": [foreign, untrusted, compound]},
        {"hooks": [foreign]},
    ]
    assert trusted["0:0"] == hashlib.sha256(json.dumps(foreign, sort_keys=True).encode()).hexdigest()
    assert trusted.get("0:1") != hashlib.sha256(json.dumps(untrusted, sort_keys=True).encode()).hexdigest()
    assert (home / "hooks.json.memu-uninstall-backup").read_bytes() == original_bytes
    for name, content in retained.items():
        assert (home / name).read_text(encoding="utf-8") == content
    snapshot = path.read_bytes()
    count = len(calls)
    assert main(["uninstall"]) == 0
    assert path.read_bytes() == snapshot
    assert len(calls) == count


def test_uninstall_missing_configuration_is_a_noop(home, monkeypatch):
    monkeypatch.setattr(uninstall.cli_prepare, "prepare", lambda _: pytest.fail("No executable needed"))
    assert main(["uninstall"]) == 0
    assert list(home.iterdir()) == []


@pytest.mark.parametrize(
    "config",
    [
        [],
        {"hooks": []},
        {"hooks": {"UserPromptSubmit": ["bad"]}},
        {"hooks": {"UserPromptSubmit": [{"hooks": ["bad"]}]}},
    ],
)
def test_uninstall_preserves_invalid_configuration(home, config):
    path = home / "hooks.json"
    path.write_text(json.dumps(config))
    original = path.read_bytes()
    assert main(["uninstall"]) == 1
    assert path.read_bytes() == original
    assert not (home / "hooks.json.memu-uninstall-backup").exists()


@pytest.mark.parametrize("concurrent_edit", [False, True])
def test_uninstall_failed_readback_preserves_configuration(home, monkeypatch, concurrent_edit):
    path = home / "hooks.json"
    original = b'{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"memu-codex prompt-hook"}]}]}}'
    path.write_bytes(original)

    class Server:
        def __init__(self, *args):
            pass

        def request(self, method, params=None):
            if method == "hooks/list" and path.read_bytes() != original:
                if concurrent_edit:
                    path.write_bytes(b'{"description":"concurrent user edit"}')
                raise RuntimeError("Read-back failed")  # noqa: TRY003
            return {}

        def notify(self, method):
            pass

        def close(self):
            pass

    monkeypatch.setattr(uninstall.cli_prepare, "prepare", lambda _: {"status": "passed", "executable": "fixture"})
    monkeypatch.setattr(uninstall.hooks, "AppServer", Server)
    assert main(["uninstall"]) == 1
    assert path.read_bytes() == (b'{"description":"concurrent user edit"}' if concurrent_edit else original)


def test_uninstall_preserves_untrusted_hook_approvals(home):
    path = home / "hooks.json"
    entry = {"command": "foreign", "sourcePath": str(path), "currentHash": "same", "key": "shifted"}
    before = {"hooks": [{**entry, "trustStatus": "untrusted"}]}
    after = {"hooks": [{**entry, "trustStatus": "trusted"}]}
    with pytest.raises(RuntimeError, match="untrusted hook"):
        uninstall._trust_updates(before, after, {"foreign"}, path)
