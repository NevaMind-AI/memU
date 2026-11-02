"""Installation scenarios use isolated homes and real stage orchestration."""

import io
import json
import os
from pathlib import Path

import pytest

from memu import config_file
from memu.hosts import host_cli, instruction
from memu.hosts.codex import install, memorize_hook, prompt_hook
from memu.hosts.codex.cli import main

READBACK = install._integration_readback
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

    async def readback(*args):
        calls.append(("readback",))

    monkeypatch.setattr(install, "_command", command)
    monkeypatch.setattr(install.cli_prepare, "prepare", prepare)
    monkeypatch.setattr(install.prompt_hook_install, "install", register)
    monkeypatch.setattr(install, "_integration_readback", readback)
    return home, base, calls


def invoke(machine, *args):
    return main(["install", "--non-interactive", "--json", "--base-dir", str(machine[1]), *args])


def evidence(tmp_path, *, deleted=False):
    for name in ("definition", "pause", "delete", "inventory"):
        (tmp_path / name).write_text("Desktop tool evidence fixture", encoding="utf-8")
    task = {
        "id": "owned-memu-task",
        "owned": True,
        "paused": True,
        "idle": True,
        "definition_file": "definition",
        "pause_evidence_file": "pause",
    }
    if deleted:
        task.update(deleted=True, delete_evidence_file="delete")
    path = tmp_path / "migration.json"
    path.write_text(
        json.dumps({
            "version": 1,
            "source": "desktop",
            "inventory_complete": True,
            "inventory_evidence_file": "inventory",
            "tasks": [task],
        }),
        encoding="utf-8",
    )
    return path


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
        options += ["--agent", "fixture-codex"]
    assert main(options) == 0
    assert observed == [str(tmp_path / ".codex")]


def test_terminal_install_completes_without_desktop_migration(machine, capsys, monkeypatch):
    before = config_file.config_path().read_bytes()
    assert invoke(machine) == 0
    output = capsys.readouterr()
    progress = [json.loads(line) for line in output.out.splitlines()]
    assert [p["stage"] for p in progress if p["status"] == "passed"] == [1, 2, 3, 4, 5]
    assert progress[-1]["complete"] is True
    assert progress[-1]["migration"] == "desktop_deferred"
    assert "Desktop 暂停旧 memU" in output.err
    assert config_file.config_path().read_bytes() == before
    assert os.environ["CODEX_HOME"] == "original-home"
    assert machine[2].index(("register",)) < machine[2].index(("readback",))
    assert invoke(machine) == 0


def test_agent_unknown_inventory_blocks_before_registration(machine, capsys):
    assert invoke(machine, "--agent") == 2
    assert ("register",) not in machine[2]
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["stage"] == 4


def test_agent_confirmed_new_install(machine):
    assert invoke(machine, "--agent", "--new-install") == 0


def test_new_install_cannot_hide_existing_automations(machine):
    task = machine[0] / "automations/foreign/automation.toml"
    task.parent.mkdir(parents=True)
    task.write_text("name='other task'", encoding="utf-8")
    assert invoke(machine, "--agent", "--new-install") == 2
    assert machine[2] == []
    assert task.read_text() == "name='other task'"


def test_desktop_handoff_registers_before_deletion_and_resumes(machine, tmp_path, capsys):
    path = evidence(tmp_path)
    assert invoke(machine, "--agent", "--migration-evidence", str(path), "--through-stage", "4") == 0
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["complete"] is False
    assert invoke(machine, "--stage", "5") == 2
    assert ("remove-instruction",) not in machine[2]
    evidence(tmp_path, deleted=True)
    assert invoke(machine, "--stage", "5") == 0
    assert machine[2].count(("register",)) == 1
    state = json.loads((machine[1] / "install-state.json").read_text())
    assert state["complete"] is True
    assert state["migration_source"] == "desktop"


@pytest.mark.parametrize("field", ["owned", "paused", "idle"])
def test_unsafe_task_blocks_before_registration(machine, tmp_path, field):
    path = evidence(tmp_path)
    data = json.loads(path.read_text())
    data["tasks"][0][field] = False
    path.write_text(json.dumps(data))
    assert invoke(machine, "--agent", "--migration-evidence", str(path)) == 2
    assert ("register",) not in machine[2]


def test_missing_evidence_files_block(machine, tmp_path):
    path = evidence(tmp_path)
    (tmp_path / "pause").unlink()
    assert invoke(machine, "--agent", "--migration-evidence", str(path)) == 2
    assert ("register",) not in machine[2]


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


def test_preserves_cursors_self_sessions_pending_results_and_logs(machine):
    base = machine[1]
    files = [
        ".session_manifest.codex.json",
        ".session_manifest.codex.json.pending",
        ".self_sessions.codex.json",
        "jobs/1.txt",
        "results/pending.json",
        "log/previous.log",
    ]
    for name in files:
        path = base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("preserved", encoding="utf-8")
    assert invoke(machine) == 0
    assert all((base / name).read_text() == "preserved" for name in files)


def test_change_during_handoff_blocks_finalization(machine):
    path = machine[1] / ".session_manifest.codex.json"
    path.write_text("before")
    assert invoke(machine, "--through-stage", "3") == 0
    path.write_text("changed")
    assert invoke(machine) == 2
    assert ("remove-instruction",) not in machine[2]


def test_active_worker_blocks_installation(machine):
    with install.workspace_lock(machine[1]) as acquired:
        assert acquired
        assert invoke(machine) == 2
    assert machine[2] == []


def test_ambiguous_legacy_skill_is_preserved(machine):
    skill = machine[0] / "skills/memu-retrieve/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("user content")
    assert invoke(machine) == 2
    assert skill.read_text() == "user content"
    assert ("remove-instruction",) not in machine[2]


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
def test_legacy_cleanup_preserves_customizations(machine, customization):
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
    assert ("remove-instruction",) not in machine[2]


def test_state_contains_no_backend_credentials(machine):
    assert invoke(machine) == 0
    assert "fixture-only" not in (machine[1] / "install-state.json").read_text()


def test_individual_stages_allow_progress_without_repeating_work(machine):
    for stage in range(1, 6):
        assert invoke(machine, "--stage", str(stage)) == 0
    assert machine[2].count(("doctor",)) == 1
    assert machine[2].count(("register",)) == 1


def test_new_install_confirmation_survives_stage_boundary(machine):
    assert invoke(machine, "--agent", "--through-stage", "3") == 0
    assert invoke(machine, "--agent", "--stage", "4", "--new-install") == 0
    assert invoke(machine, "--stage", "5") == 0


@pytest.mark.parametrize("backend", ["cloud", "local"])
def test_backend_uses_shared_config_writer_and_doctor(machine, monkeypatch, tmp_path, backend, capsys):
    config_file.config_path().write_text("# user setting\nMEMU_CLAUDE_MODEL=existing-model\n")
    observed = []

    async def doctor(spec, args):
        observed.append(config_file.read())
        return 0

    monkeypatch.setattr(install, "_command", COMMAND)
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
    assert invoke(machine, "--through-stage", "2", *options) == 0
    assert len(observed) == 1
    assert observed[0]["MEMU_MEMORY_MODE"] == backend
    assert observed[0]["MEMU_CLAUDE_MODEL"] == "existing-model"
    assert "# user setting" in config_file.config_path().read_text()
    assert "sensitive-fixture" not in capsys.readouterr().out
    assert "sensitive-fixture" not in (machine[1] / "install-state.json").read_text()


def test_interactive_install_configures_a_backend_when_only_client_metadata_exists(machine, monkeypatch, tmp_path):
    config_file.config_path().write_text("MEMU_CLIENT_ID=existing-client\n")
    inputs = iter(["local", str(tmp_path / "memory.sqlite3"), "openai", "fixture-model", "http://localhost:11434/v1"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr(install.getpass, "getpass", lambda _: "fixture-secret")
    monkeypatch.setattr(install, "_command", COMMAND)
    observed = []

    async def doctor(spec, args):
        observed.append(config_file.read())
        return 0

    monkeypatch.setattr(host_cli, "_cmd_doctor", doctor)
    assert main(["install", "--json", "--base-dir", str(machine[1]), "--through-stage", "2"]) == 0
    assert observed[0]["MEMU_CLIENT_ID"] == "existing-client"
    assert observed[0]["MEMU_MEMORY_MODE"] == "local"
    assert observed[0]["MEMU_BASE_URL"] == "http://localhost:11434/v1"
    assert observed[0]["MEMU_DB"] == str((tmp_path / "memory.sqlite3").resolve())


def test_desktop_definition_change_blocks_cleanup(machine, tmp_path):
    path = evidence(tmp_path)
    assert invoke(machine, "--agent", "--migration-evidence", str(path), "--through-stage", "4") == 0
    evidence(tmp_path, deleted=True)
    (tmp_path / "definition").write_text("changed definition")
    assert invoke(machine, "--stage", "5") == 2
    assert ("remove-instruction",) not in machine[2]


def test_missing_inventory_artifact_blocks_even_an_empty_agent_report(machine, tmp_path):
    path = evidence(tmp_path)
    data = json.loads(path.read_text())
    data["tasks"] = []
    path.write_text(json.dumps(data))
    (tmp_path / "inventory").unlink()
    assert invoke(machine, "--agent", "--migration-evidence", str(path)) == 2
    assert ("register",) not in machine[2]


def test_stage_cannot_skip_prerequisites(machine):
    assert invoke(machine, "--stage", "4") == 2
    assert machine[2] == []


def test_finalization_detects_changed_backend(machine):
    assert invoke(machine, "--through-stage", "4") == 0
    config_file.write_values({"MEMU_CLOUD_API_KEY": "changed-fixture"})
    assert invoke(machine, "--stage", "5") == 2
    assert ("remove-instruction",) not in machine[2]


def test_registration_failure_can_be_retried(machine, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("untrusted hook")  # noqa: TRY003

    with monkeypatch.context() as patch:
        patch.setattr(install.prompt_hook_install, "install", fail)
        assert invoke(machine) == 1
    state = json.loads((machine[1] / "install-state.json").read_text())
    assert state["last_stage"] == 3
    assert invoke(machine, "--stage", "4") == 0
    assert invoke(machine, "--stage", "5") == 0


@pytest.mark.parametrize("trusted", [True, False])
def test_real_registration_and_final_readback_preserve_foreign_hooks(machine, monkeypatch, trusted):
    home, _, _ = machine
    hooks = home / "hooks.json"
    hooks.write_text(
        json.dumps({
            "other": "kept",
            "hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": "third-party"}]}]},
        })
    )

    class Server:
        def __init__(self, executable, cwd, codex_home):
            assert codex_home == home

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
    monkeypatch.setattr(install, "_integration_readback", READBACK)
    monkeypatch.setattr(install.prompt_hook_install.sys, "argv", [str(home / "memu-codex.exe")])
    assert invoke(machine) == (0 if trusted else 1)
    data = json.loads(hooks.read_text())
    assert data["other"] == "kept"
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
