import json

from memu.hosts.codex import prompt_hook_install as installer


def test_install_merges_hook_trusts_and_preserves_unrelated_config(tmp_path, monkeypatch):
    hooks_file = tmp_path / "hooks.json"
    hooks_file.write_text(
        json.dumps({
            "other": {"preserved": True},
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "hooks": [
                            {"type": "command", "command": '"C:/old/memu-codex.exe" prompt-hook'},
                            {"type": "command", "command": "custom-command"},
                        ]
                    }
                ]
            },
        }),
        encoding="utf-8",
    )
    calls = []

    class FakeServer:
        def __init__(self, executable, cwd):
            pass

        def request(self, method, params=None):
            calls.append((method, params))
            if method != "hooks/list":
                return {}
            config = json.loads(hooks_file.read_text(encoding="utf-8"))
            command = config["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
            return {
                "data": [
                    {
                        "hooks": [
                            {
                                "command": command,
                                "sourcePath": str(hooks_file),
                                "key": "hook:key",
                                "currentHash": "sha256:current",
                                "trustStatus": "trusted"
                                if sum(name == "config/value/write" for name, _ in calls)
                                else "untrusted",
                            }
                        ]
                    }
                ]
            }

        def notify(self, method):
            calls.append((method, None))

        def close(self):
            pass

    monkeypatch.setattr(installer, "AppServer", FakeServer)
    monkeypatch.setattr(installer.sys, "argv", [str(tmp_path / "memu-codex.exe")])
    installer.install("codex", hooks_file, tmp_path)

    config = json.loads(hooks_file.read_text(encoding="utf-8"))
    entries = config["hooks"]["UserPromptSubmit"][0]["hooks"]
    assert config["other"] == {"preserved": True}
    assert len(entries) == 2
    expected_command = (
        installer.subprocess.list2cmdline([str(tmp_path / "memu-codex.exe"), "prompt-hook"])
        if installer.os.name == "nt"
        else installer.shlex.join([str(tmp_path / "memu-codex.exe"), "prompt-hook"])
    )
    assert entries[0]["command"] == expected_command
    assert entries[1]["command"] == "custom-command"
    assert (tmp_path / "hooks.json.memu-backup").exists()
    trust = next(params for method, params in calls if method == "config/value/write")
    assert trust["keyPath"] == 'hooks.state."hook:key".trusted_hash'
    assert trust["value"] == "sha256:current"
