import argparse
import json
import subprocess
import sys

import pytest

from memu.hosts.codex import prompt_hook_install as installer


@pytest.mark.parametrize("previous", ['["memu-codex", "hook"]', '["other-notifier", "--flag"]'])
def test_install_merges_hook_trusts_and_preserves_unrelated_config(tmp_path, monkeypatch, previous):
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
        def __init__(self, executable, cwd, codex_home):
            assert codex_home == hooks_file.parent

        def request(self, method, params=None):
            calls.append((method, params))
            if method != "hooks/list":
                return {}
            config = json.loads(hooks_file.read_text(encoding="utf-8"))
            return {
                "data": [
                    {
                        "hooks": [
                            {
                                "command": hook["command"],
                                "sourcePath": str(hooks_file),
                                "key": "hook:key",
                                "currentHash": "sha256:current",
                                "trustStatus": "trusted"
                                if any(name == "config/value/write" for name, _ in calls)
                                else "untrusted",
                            }
                            for group in config["hooks"]["UserPromptSubmit"]
                            for hook in group["hooks"]
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
    base = tmp_path / "custom base"
    config_file = tmp_path / "config.toml"
    config_file.write_text(f'notify = {previous}\nmodel = "kept"\n')
    installer.install("codex", hooks_file, tmp_path, str(base))
    installer.install("codex", hooks_file, tmp_path, str(base))
    expected = 'model = "kept"\n' if "memu-codex" in previous else f'notify = {previous}\nmodel = "kept"\n'
    assert config_file.read_text() == expected

    config = json.loads(hooks_file.read_text(encoding="utf-8"))
    entries = config["hooks"]["UserPromptSubmit"][0]["hooks"]
    all_hooks = [hook for group in config["hooks"]["UserPromptSubmit"] for hook in group["hooks"]]
    assert len(all_hooks) == 3
    assert "memorize-hook" in all_hooks[-1]["command"]
    assert str(base) in all_hooks[-1]["command"]
    assert config["other"] == {"preserved": True}
    assert len(entries) == 2
    expected_command = (
        "& '" + str(tmp_path / "memu-codex.exe").replace("'", "''") + "' prompt-hook"
        if installer.sys.platform == "win32"
        else installer.shlex.join([str(tmp_path / "memu-codex.exe"), "prompt-hook"])
    )
    assert entries[0]["command"] == expected_command
    assert entries[1]["command"] == "custom-command"
    assert (tmp_path / "hooks.json.memu-backup").exists()
    trust = next(params for method, params in calls if method == "config/value/write")
    assert trust["keyPath"] == 'hooks.state."hook:key".trusted_hash'
    assert trust["value"] == "sha256:current"


@pytest.mark.parametrize(
    "command",
    [
        "memu-codex prompt-hook",
        '"C:/Program Files/memu/memu-codex.exe" prompt-hook',
        "& 'C:/User''s Tools/memu-codex.exe' prompt-hook",
        r"C:\tools\memu-codex.exe prompt-hook",
    ],
)
def test_owns_only_direct_memu_commands(command):
    assert installer._owns_command(command)


@pytest.mark.parametrize(
    "command",
    [
        "/tools/memu-codex-custom prompt-hook",
        "memu-codex prompt-hook-extra",
        "memu-codex retrieve prompt-hook",
        "wrapper memu-codex prompt-hook",
        "memu-codex prompt-hook && other-command",
    ],
)
def test_preserves_unrelated_commands(command):
    groups = [{"hooks": [{"type": "command", "command": command}]}]
    installer._definition(groups, "memu-codex prompt-hook")
    assert groups[0]["hooks"][0]["command"] == command
    assert len(groups) == 2


def test_windows_command_escapes_spaces_and_apostrophes(tmp_path, monkeypatch):
    executable = tmp_path / "User's Tools" / "memu-codex.exe"
    monkeypatch.setattr(installer.sys, "argv", [str(executable)])
    monkeypatch.setattr(installer.sys, "platform", "win32")
    assert installer._command() == "& '" + str(executable.resolve()).replace("'", "''") + "' prompt-hook"


def test_hooks_default_uses_codex_home_and_explicit_override(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "custom-home"))
    parser = argparse.ArgumentParser()
    installer.register(parser.add_subparsers())
    assert parser.parse_args(["install-prompt-hook"]).hooks_file == tmp_path / "custom-home" / "hooks.json"
    explicit = tmp_path / "explicit-home" / "hooks.json"
    assert parser.parse_args(["install-prompt-hook", "--hooks-file", str(explicit)]).hooks_file == explicit


def test_app_server_uses_selected_home_and_drains_diagnostics(tmp_path, monkeypatch, capfd):
    popen = subprocess.Popen
    script = r"""import json, os, sys
sys.stderr.write('x' * 131072 + '\n')
sys.stderr.flush()
for line in sys.stdin:
    request = json.loads(line)
    print(json.dumps({'id': request['id'], 'result': {'home': os.environ['CODEX_HOME']}}), flush=True)
"""

    def start(argv, **kwargs):
        assert "stderr" not in kwargs
        return popen([sys.executable, "-u", "-c", script], **kwargs)

    monkeypatch.setattr(installer.subprocess, "Popen", start)
    selected_home = tmp_path / "selected-home"
    server = installer.AppServer("codex", tmp_path, selected_home)
    try:
        assert server.request("initialize") == {"home": str(selected_home)}
    finally:
        server.close()
    assert "x" * 131072 in capfd.readouterr().err


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell command execution")
def test_windows_command_executes_path_with_spaces_and_apostrophe(tmp_path, monkeypatch):
    executable = tmp_path / "User's Tools" / "memu-codex.cmd"
    executable.parent.mkdir()
    executable.write_text("@echo HOOK_QUOTE_OK\n", encoding="ascii")
    monkeypatch.setattr(installer.sys, "argv", [str(executable)])
    powershell = installer.shutil.which("powershell.exe")
    assert powershell is not None
    result = subprocess.run(  # noqa: S603
        [powershell, "-NoProfile", "-NonInteractive", "-Command", installer._command()],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "HOOK_QUOTE_OK" in result.stdout


@pytest.mark.parametrize("notify", ['["other-notifier", "--flag"]', '["memu-codex", "hook"]'])
def test_trust_failure_keeps_existing_notify(tmp_path, monkeypatch, notify):
    hooks_file = tmp_path / "hooks.json"
    config = tmp_path / "config.toml"
    original = f"notify = {notify}\n"
    config.write_text(original)

    class FailedServer:
        def __init__(self, *args):
            pass

        def request(self, *args):
            return {}

        def notify(self, *args):
            pass

        def close(self):
            pass

    monkeypatch.setattr(installer, "AppServer", FailedServer)
    with pytest.raises(RuntimeError, match="Expected one loaded"):
        installer.install("codex", hooks_file, tmp_path)
    assert config.read_text() == original
