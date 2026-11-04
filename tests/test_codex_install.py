"""One-shot installation scenarios use isolated homes and real orchestration."""

import io
import json
import os
from pathlib import Path

import pytest

from memu import config_file, events
from memu.hosts import host_cli, instruction
from memu.hosts.codex import install, memorize_hook, prompt_hook
from memu.hosts.codex.cli import main

REGISTER_HOOKS = install.prompt_hook_install.install
COMMAND = install._command


@pytest.fixture
def machine(tmp_path, monkeypatch):
    home = tmp_path / "codex"
    home.mkdir()
    base = tmp_path / "state"
    base.mkdir()
    monkeypatch.setattr(install, "_home", lambda: home)
    monkeypatch.setenv("CODEX_HOME", "original-home")
    config_file.write_values({"MEMU_MEMORY_MODE": "cloud", "MEMU_CLOUD_API_KEY": "fixture-only"})
    calls = []

    async def command(argv):
        calls.append(tuple(argv))
        return 0

    def prepare(*args, **kwargs):
        calls.append(("prepare-cli",))
        return {"status": "passed", "executable": str(tmp_path / "codex.exe")}

    def register(*args, **kwargs):
        calls.append(("register",))
        assert kwargs["default_home"] is True
        assert args[1] == home / "hooks.json"
        (home / "hooks.json").write_text('{"hooks": {"UserPromptSubmit": []}}', encoding="utf-8")

    monkeypatch.setattr(install, "_command", command)
    monkeypatch.setattr(install.cli_prepare, "prepare", prepare)
    monkeypatch.setattr(install.prompt_hook_install, "install", register)
    return home, base, calls


def invoke(machine, *args):
    return main(["install", "--non-interactive", "--json", "--base-dir", str(machine[1]), *args])


@pytest.mark.parametrize("hook", ["prompt-hook", "memorize-hook"])
def test_registered_handlers_use_default_home_in_child_environment(machine, monkeypatch, tmp_path, hook):
    observed = []
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    options = [hook, "--base-dir", str(machine[1]), "--default-home"]
    if hook == "prompt-hook":
        monkeypatch.setattr(prompt_hook, "_retrieve", lambda trace: observed.append(os.environ["CODEX_HOME"]))
    else:
        monkeypatch.setattr("sys.stdin", io.StringIO('{"hook_event_name": "UserPromptSubmit"}'))
        monkeypatch.delenv(memorize_hook.BACKGROUND_ENV, raising=False)

        def launch(argv, layout, host):
            observed.append(os.environ["CODEX_HOME"])
            return machine[1] / "log.json"

        monkeypatch.setattr(memorize_hook.notify_console, "launch_background", launch)
        monkeypatch.setattr(memorize_hook, "_startup_snapshot", lambda path: {"status": "started"})
        monkeypatch.setattr(memorize_hook.cli_prepare, "_discover", lambda _: tmp_path / "codex.exe")
    assert main(options) == 0
    assert observed == [str(tmp_path / ".codex")]


def test_one_invocation_verifies_installation_and_can_be_repeated(machine, capsys, monkeypatch):
    before = config_file.config_path().read_bytes()
    recorded = []
    monkeypatch.setattr(events, "record", lambda name, **kwargs: recorded.append(name))
    monkeypatch.setattr(events, "flush", lambda: pytest.fail("Installation must not drain historical telemetry"))
    assert invoke(machine) == 0
    progress = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [p["stage"] for p in progress if p["status"] == "passed"] == [1, 2, 3, 4, 5]
    assert all(p.get("complete") is not True for p in progress[:-1])
    assert progress[-1]["complete"] is True
    assert "If you use Codex Desktop" in progress[-1]["notice"]
    assert "pause or remove" in progress[-1]["notice"]
    assert [p["elapsed_ms"] for p in progress] == sorted(p["elapsed_ms"] for p in progress)
    assert machine[2] == [("doctor", "--backend-only"), ("prepare-cli",), ("register",), ("remove-instruction",)]
    assert recorded == [events.CLI_INSTALL_STARTED, events.CLI_INSTALL_SUCCEEDED]
    assert config_file.config_path().read_bytes() == before
    assert os.environ["CODEX_HOME"] == "original-home"
    assert not (machine[1] / "install-state.json").exists()
    assert invoke(machine) == 0


def test_existing_tasks_and_processing_data_are_preserved_without_inventory(machine, monkeypatch):
    home, base, _ = machine
    task = home / "automations/user-task/automation.toml"
    task.parent.mkdir(parents=True)
    task.write_text("name='my memU schedule'", encoding="utf-8")
    files = [
        ".session_manifest.codex.json",
        ".session_manifest.codex.json.pending",
        ".self_sessions.codex.json",
        "jobs/1.txt",
        "results/pending.json",
        "log/previous.log",
        "install-state.json",
    ]
    for name in files:
        path = base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("preserved", encoding="utf-8")
    read_bytes = Path.read_bytes
    glob = Path.glob

    def read(path):
        assert not path.is_relative_to(base), "Installation must not hash historical processing files"
        return read_bytes(path)

    def discover(path, pattern):
        assert path != home / "automations", "Installation must not inspect Desktop tasks"
        return glob(path, pattern)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_bytes", read)
        patch.setattr(Path, "glob", discover)
        assert invoke(machine) == 0
    assert all((base / name).read_text() == "preserved" for name in files)
    assert task.read_text() == "name='my memU schedule'"


@pytest.mark.parametrize(
    ("language", "title", "notice"),
    [
        ("en", "Checking installation conditions", "If you use Codex Desktop"),
        ("zh", "检查安装条件", "如果你使用 Codex Desktop"),
    ],
)
def test_language_selects_progress_and_final_notice(machine, capsys, language, title, notice):
    assert invoke(machine, "--language", language) == 0
    progress = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert progress[0]["title"] == title
    assert notice in progress[-1]["notice"]
    assert all("notice" not in p for p in progress[:-1])


def test_human_output_includes_progress_and_user_follow_up(machine, capsys):
    assert main(["install", "--non-interactive", "--language", "zh", "--base-dir", str(machine[1])]) == 0
    output = capsys.readouterr().out
    assert "🔎  1/5  检查安装条件" in output
    assert "✨  5/5  完成安装检查" in output
    assert "🎉 memU 安装完成" in output
    assert "started" not in output and "passed" not in output
    assert output.count(install.NOTICE) == 1


@pytest.mark.parametrize("json_output", [True, False])
def test_codex_download_failure_explains_cause_and_next_step(machine, monkeypatch, capsys, json_output):
    monkeypatch.setattr(
        install.cli_prepare,
        "prepare",
        lambda *a, **k: {
            "status": "failed",
            "reason": "download_http_error",
            "http_status": 403,
            "detail": "Official Codex installer download failed: HTTP 403 (Forbidden).",
        },
    )
    options = ["install", "--non-interactive", "--language", "zh", "--base-dir", str(machine[1])]
    if json_output:
        options.append("--json")
    assert main(options) == 1
    output = capsys.readouterr().out
    assert "HTTP 403" in output
    assert "--codex PATH" in output
    assert "RuntimeError" not in output
    assert ("register",) not in machine[2]
    if json_output:
        assert json.loads(output.splitlines()[-1])["status"] == "failed"
    else:
        assert "❌  安装未完成" in output


def test_codex_install_prompt_remains_visible(machine, monkeypatch, capsys):
    choices = []

    def prepare(*a, **kw):
        if not kw.get("install_missing"):
            return {"status": "blocked", "reason": "missing", "detail": "missing"}
        return {"status": "passed", "executable": "codex"}

    def confirm(prompt):
        print(prompt, end="")
        choices.append(prompt)
        return "y"

    monkeypatch.setattr(install.cli_prepare, "prepare", prepare)
    monkeypatch.setattr("builtins.input", confirm)
    assert main(["install", "--language", "zh", "--base-dir", str(machine[1])]) == 0
    assert len(choices) == 1
    assert "是否使用官方安装器补装 Codex" in capsys.readouterr().out


def test_interactive_language_choice_applies_to_each_invocation(machine, monkeypatch, capsys):
    prompts = []

    def choose(prompt):
        prompts.append(prompt)
        return "zh"

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", choose)
    for _ in range(2):
        assert main(["install", "--base-dir", str(machine[1]), "--json"]) == 0
        assert json.loads(capsys.readouterr().out.splitlines()[-1])["title"] == "完成安装检查"
    assert len(prompts) == 2
    assert all("en/zh" in prompt for prompt in prompts)
    assert invoke(machine, "--language", "en") == 0
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["title"] == "Completing installation checks"
    assert len(prompts) == 2


def test_noninteractive_language_defaults_to_english_and_localizes_blockers(machine, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: pytest.fail("Must not prompt"))
    assert invoke(machine, "--language", "zh") == 0
    capsys.readouterr()
    assert invoke(machine) == 0
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["title"] == "Completing installation checks"
    config_file.config_path().unlink()
    assert invoke(machine) == 2
    blocker = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert blocker["status"] == "blocked"
    assert "backend is not configured" in blocker["detail"]
    assert "notice" not in blocker


def test_doctor_failure_stops_before_host_and_hooks(machine, monkeypatch):
    async def fail(argv):
        return 1

    monkeypatch.setattr(install, "_command", fail)
    assert invoke(machine) == 2
    assert machine[2] == []


def test_noninteractive_unconfigured_backend_does_not_prompt(machine, monkeypatch):
    config_file.config_path().unlink()
    monkeypatch.setattr("builtins.input", lambda _: pytest.fail("Must not prompt"))
    assert invoke(machine) == 2
    assert machine[2] == []


def test_active_worker_does_not_block_configuration_only_installation(machine):
    with install.installation.workspace_lock(machine[1]) as acquired:
        assert acquired
        assert invoke(machine) == 0
    assert machine[2].count(("register",)) == 1


def test_concurrent_installer_blocks_without_retrying(machine, capsys):
    lock_dir = machine[1] / ".install"
    lock_dir.mkdir()
    with install.installation.workspace_lock(lock_dir) as acquired:
        assert acquired
        assert invoke(machine) == 2
    assert machine[2] == []
    progress = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(progress) == 1
    assert progress[0]["status"] == "blocked"
    assert "Another installer is running" in progress[0]["detail"]


def test_malformed_hooks_not_overwritten(machine):
    hooks = machine[0] / "hooks.json"
    hooks.write_text("not json")
    assert invoke(machine) == 1
    assert hooks.read_text() == "not json"
    assert machine[2] == []


def test_legacy_cleanup_removes_owned_entries_and_preserves_user_text(machine, monkeypatch):
    home = machine[0]
    skill = home / "skills/memu-retrieve/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(instruction.skill_document("memu-codex"), encoding="utf-8")
    agents = home / "AGENTS.md"
    agents.write_text("user instruction\n\n" + instruction.block("memu-codex", skill=True), encoding="utf-8")

    async def command(argv):
        if argv[0] == "remove-instruction":
            return await COMMAND([*argv, "--path", str(agents), "--skills-dir", str(home / "skills")])
        return 0

    monkeypatch.setattr(install, "_command", command)
    assert invoke(machine) == 0
    assert not skill.parent.exists()
    assert agents.read_text(encoding="utf-8").strip() == "user instruction"


@pytest.mark.parametrize("customization", ["skill-edit", "extra-file", "instruction-edit"])
def test_legacy_cleanup_preserves_customizations_before_registration(machine, customization):
    home = machine[0]
    skill = home / "skills/memu-retrieve/SKILL.md"
    skill.parent.mkdir(parents=True)
    original = instruction.skill_document("memu-codex")
    skill.write_text(original + ("user note" if customization == "skill-edit" else ""), encoding="utf-8")
    if customization == "extra-file":
        (skill.parent / "notes.txt").write_text("user note")
    if customization == "instruction-edit":
        block = instruction.block("memu-codex", skill=True).replace("Before answering", "User modified rule")
        (home / "AGENTS.md").write_text(block, encoding="utf-8")
    before = skill.read_bytes()
    assert invoke(machine) == 2
    assert skill.read_bytes() == before
    assert machine[2] == []


@pytest.mark.parametrize("backend", ["cloud", "local"])
def test_backend_uses_shared_config_writer_and_doctor(machine, monkeypatch, tmp_path, backend, capsys):
    config_file.config_path().write_text("# user setting\nMEMU_CLAUDE_MODEL=existing-model\n")
    observed = []

    async def doctor(spec, args):
        observed.append(config_file.read())
        return 0

    async def command(argv):
        return 0 if argv[0] == "remove-instruction" else await COMMAND(argv)

    monkeypatch.setattr(install, "_command", command)
    monkeypatch.setattr(host_cli, "_cmd_doctor", doctor)
    options = ["--backend", backend]
    if backend == "cloud":
        options += ["--cloud-api-key", "sensitive-fixture"]
    else:
        options += [
            "--db",
            str(tmp_path / "memory.sqlite3"),
            "--embed-provider",
            "openai",
            "--embed-model",
            "fixture-model",
            "--embed-api-key",
            "sensitive-fixture",
        ]
    assert invoke(machine, *options) == 0
    assert len(observed) == 1
    assert observed[0]["MEMU_MEMORY_MODE"] == backend
    assert observed[0]["MEMU_CLAUDE_MODEL"] == "existing-model"
    assert "# user setting" in config_file.config_path().read_text()
    assert "sensitive-fixture" not in capsys.readouterr().out
    assert not (machine[1] / "install-state.json").exists()


def test_interactive_install_configures_a_backend_when_only_client_metadata_exists(machine, monkeypatch, tmp_path):
    config_file.config_path().write_text("MEMU_CLIENT_ID=existing-client\n")
    inputs = iter(["local", str(tmp_path / "memory.sqlite3"), "openai", "fixture-model", "http://localhost:11434/v1"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr(install.installation.getpass, "getpass", lambda _: "fixture-secret")
    observed = []

    async def doctor(spec, args):
        observed.append(config_file.read())
        return 0

    async def command(argv):
        return 0 if argv[0] == "remove-instruction" else await COMMAND(argv)

    monkeypatch.setattr(install, "_command", command)
    monkeypatch.setattr(host_cli, "_cmd_doctor", doctor)
    assert main(["install", "--json", "--language", "en", "--base-dir", str(machine[1])]) == 0
    assert observed[0]["MEMU_CLIENT_ID"] == "existing-client"
    assert observed[0]["MEMU_MEMORY_MODE"] == "local"
    assert observed[0]["MEMU_BASE_URL"] == "http://localhost:11434/v1"
    assert observed[0]["MEMU_DB"] == str((tmp_path / "memory.sqlite3").resolve())


def test_registration_failure_can_be_retried_as_a_whole(machine, monkeypatch, capsys):
    def fail(*args, **kwargs):
        raise RuntimeError("fixture-only-secret")

    with monkeypatch.context() as patch:
        patch.setattr(install.prompt_hook_install, "install", fail)
        assert invoke(machine) == 1
    output = capsys.readouterr().out
    assert "fixture-only-secret" not in output
    assert json.loads(output.splitlines()[-1])["complete"] is False
    assert ("remove-instruction",) not in machine[2]
    assert os.environ["CODEX_HOME"] == "original-home"
    assert invoke(machine) == 0


@pytest.mark.parametrize("trusted", [True, False])
def test_real_registration_verifies_both_hooks_in_one_server_and_preserves_foreign_hooks(machine, monkeypatch, trusted):
    home, _, _ = machine
    hooks = home / "hooks.json"
    hooks.write_text(
        json.dumps({
            "description": "kept",
            "hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": "third-party"}]}]},
        })
    )
    starts = []

    class Server:
        def __init__(self, executable, cwd, codex_home):
            assert codex_home == home
            starts.append(executable)

        def request(self, method, params=None):
            if method != "hooks/list":
                return {}
            data = json.loads(hooks.read_text())
            return {
                "data": [
                    {
                        "hooks": [
                            {
                                "command": hook["command"],
                                "sourcePath": str(hooks),
                                "key": hook["command"],
                                "currentHash": "fixture-hash",
                                "trustStatus": "trusted" if trusted else "untrusted",
                                "async": hook.get("async", False),
                            }
                            for group in data["hooks"]["UserPromptSubmit"]
                            for hook in group["hooks"]
                        ]
                    }
                ]
            }

        def notify(self, method):
            pass

        def close(self):
            pass

    monkeypatch.setattr(install.prompt_hook_install, "AppServer", Server)
    monkeypatch.setattr(install.prompt_hook_install, "install", REGISTER_HOOKS)
    monkeypatch.setattr(install.prompt_hook_install.sys, "argv", [str(home / "memu-codex.exe")])
    assert invoke(machine) == (0 if trusted else 1)
    assert len(starts) == 1
    data = json.loads(hooks.read_text())
    assert data["description"] == "kept"
    assert data["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"] == "third-party"
    commands = [
        hook["command"]
        for group in data["hooks"]["UserPromptSubmit"]
        for hook in group["hooks"]
        if hook["command"] != "third-party"
    ]
    assert len(commands) == 2
    assert all("--default-home" in command for command in commands)
    if trusted:
        assert invoke(machine) == 0
        data = json.loads(hooks.read_text())
        assert sum(len(group["hooks"]) for group in data["hooks"]["UserPromptSubmit"]) == 3


@pytest.mark.parametrize("where", ["language", "backend", "codex"])
@pytest.mark.parametrize("interruption", [EOFError, KeyboardInterrupt])
def test_install_input_ends_cleanly(machine, monkeypatch, capsys, where, interruption):
    def stop(_):
        raise interruption

    monkeypatch.setattr("builtins.input", stop)
    monkeypatch.setattr(events, "flush", lambda: pytest.fail("Cancellation must not flush telemetry"))
    options = ["install", "--base-dir", str(machine[1]), "--json"]
    if where == "language":
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    else:
        options += ["--language", "zh"]
    if where == "backend":
        config_file.config_path().unlink()
    if where == "codex":
        monkeypatch.setattr(
            install.cli_prepare,
            "prepare",
            lambda *a, **k: {
                "status": "blocked",
                "reason": "missing",
                "detail": "missing",
            },
        )
    assert main(options) == (130 if interruption is KeyboardInterrupt else 2)
    output = capsys.readouterr()
    result = json.loads(output.out.splitlines()[-1])
    assert result["status"] == ("cancelled" if interruption is KeyboardInterrupt else "blocked")
    assert result["complete"] is False
    assert "Traceback" not in output.err
    assert os.environ["CODEX_HOME"] == "original-home"
    assert ("register",) not in machine[2]


def test_cancel_during_async_installation_returns_130(machine, monkeypatch, capsys):
    import asyncio

    async def cancel(argv):
        raise asyncio.CancelledError

    monkeypatch.setattr(install, "_command", cancel)
    monkeypatch.setattr(events, "flush", lambda: pytest.fail("Cancellation must not flush telemetry"))
    assert invoke(machine) == 130
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["status"] == "cancelled"
