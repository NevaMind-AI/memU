import io
import json
import os
import subprocess
import sys

import pytest

from memu.hosts.bridging import Layout
from memu.hosts.codex import memorize_hook, prompt_hook, prompt_hook_install, query_extraction
from memu.hosts.codex.cli import main
from memu.hosts.codex.environment import codex_environment


@pytest.mark.parametrize("inherited", [None, "inherited-home"])
@pytest.mark.parametrize("explicit", [False, True])
def test_home_binding_restores_environment(tmp_path, monkeypatch, inherited, explicit):
    if inherited is None:
        monkeypatch.delenv("CODEX_HOME", raising=False)
    else:
        monkeypatch.setenv("CODEX_HOME", inherited)
    home = tmp_path / "user's codex home"
    with pytest.raises(RuntimeError), codex_environment(str(home) if explicit else None):
        expected = str(home.resolve()) if explicit else inherited
        assert os.environ.get("CODEX_HOME") == expected
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c", "import json,os; print(json.dumps(os.environ.get('CODEX_HOME')))"],
            capture_output=True,
            check=True,
            timeout=5,
        )
        assert json.loads(result.stdout) == expected
        raise RuntimeError
    assert os.environ.get("CODEX_HOME") == inherited


@pytest.mark.parametrize("handler", ["prompt-hook", "memorize-hook"])
def test_submit_uses_registered_home(tmp_path, monkeypatch, capsys, handler):
    monkeypatch.setenv("CODEX_HOME", "wrong-home")
    monkeypatch.delenv(memorize_hook.BACKGROUND_ENV, raising=False)
    home = tmp_path / "user's codex home"
    seen = []
    event = {"hook_event_name": "UserPromptSubmit", "prompt": "short prompt"}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))

    def retrieve(argv, **kwargs):
        seen.append(os.environ["CODEX_HOME"])
        return subprocess.CompletedProcess(argv, 0, b'{"segments":[]}', b"")

    def launch(*args):
        seen.append(os.environ["CODEX_HOME"])
        log = tmp_path / "worker.log"
        log.write_text("=== MEMORIZE status=started ===\n")
        return log

    monkeypatch.setattr(prompt_hook.subprocess, "run", retrieve)
    monkeypatch.setattr(memorize_hook.notify_console, "launch_background", launch)
    argv = [handler, "--codex-home", str(home), "--base-dir", str(tmp_path)]
    if handler == "memorize-hook":
        argv += ["--agent", "codex"]
    assert main(argv) == 0
    assert seen == [str(home.resolve())]
    assert os.environ["CODEX_HOME"] == "wrong-home"
    capsys.readouterr()


def test_final_codex_children_inherit_bound_home(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CODEX_HOME", "wrong-home")
    home = str((tmp_path / "selected home").resolve())
    output = tmp_path / "extraction-home.txt"
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    with codex_environment(home):
        query_extraction._run(
            [
                sys.executable,
                "-c",
                "import os,pathlib,sys; pathlib.Path(sys.argv[1]).write_text(os.environ['CODEX_HOME'], encoding='utf-8')",
                str(output),
            ],
            b"",
            tmp_path,
            flags,
        )
        memorize_hook.notify_console.stream_agent(
            [sys.executable, "-c", "import os; print('BOUND_HOME=' + os.environ['CODEX_HOME'])"],
            Layout.default("codex", tmp_path),
            "probe",
            5,
        )
    assert output.read_text(encoding="utf-8") == home
    assert "BOUND_HOME=" + home in capsys.readouterr().out
    assert os.environ["CODEX_HOME"] == "wrong-home"


@pytest.mark.parametrize(
    "command,subcommand",
    [
        ("memu-codex prompt-hook --base-dir '/host state' --codex-home '/user''s codex'", "prompt-hook"),
        ("memu-codex prompt-hook --codex-home '/codex' --base-dir '/host'", "prompt-hook"),
        (
            "memu-codex memorize-hook --codex-home '/codex' --agent '/bin/codex' --session-dir '/codex/sessions'",
            "memorize-hook",
        ),
    ],
)
def test_owned_commands_with_home(command, subcommand):
    assert prompt_hook_install._owns_command(command, subcommand)
    if subcommand == "prompt-hook":
        assert not prompt_hook_install._owns_command(command + " && other-command", subcommand)
