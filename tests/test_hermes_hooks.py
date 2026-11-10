from __future__ import annotations

import importlib.util
import json
from types import SimpleNamespace

import pytest

from memu import config_file
from memu.hosts import installation, templates
from memu.hosts.hermes import hook, hook_install, install
from memu.hosts.hermes.cli import main
from memu.hosts.hooks.admission import workspace_lock


@pytest.fixture
def machine(tmp_path, monkeypatch):
    home, base = tmp_path / "hermes", tmp_path / "state"
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(install.shutil, "which", lambda _: "hermes")
    monkeypatch.setattr(config_file, "read", lambda: {"MEMU_MEMORY_MODE": "cloud", "MEMU_CLOUD_API_KEY": "test"})
    monkeypatch.setattr(installation.events, "record", lambda *a, **k: None)
    calls = []

    async def command(argv):
        calls.append(argv)
        return 0

    def plugin_command(action):
        calls.append(action)
        if action == "remove":
            import shutil

            shutil.rmtree(hook_install.target())

    monkeypatch.setattr(install, "_command", command)
    monkeypatch.setattr(hook_install, "command", plugin_command)
    return home, base, calls


def test_plugin_command_does_not_wait_for_hidden_input(monkeypatch):
    import sys

    run = hook_install.subprocess.run
    monkeypatch.setattr(hook_install.shutil, "which", lambda _: sys.executable)

    def interactive_command(argv, **kwargs):
        assert kwargs["stdin"] == hook_install.subprocess.DEVNULL
        return run(
            [sys.executable, "-c", "try:\n input('Grant tool override? [y/N] ')\nexcept EOFError:\n pass"],
            **kwargs,
        )

    monkeypatch.setattr(hook_install.subprocess, "run", interactive_command)
    hook_install.command("enable")


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [0, 1])
async def test_installer_backend_doctor_uses_real_command_dispatch(monkeypatch, status):
    from memu.hosts import host_cli
    from memu.hosts.hermes.cli import SPEC

    async def backend(spec, args):
        assert spec is SPEC
        assert args.backend_only is True
        return status

    monkeypatch.setattr(host_cli, "_cmd_backend_doctor", backend)
    assert await install._command(["doctor", "--backend-only"]) == status


def test_install_and_uninstall_preserve_settings_and_memory(machine, capsys):
    home, base, calls = machine
    home.mkdir()
    settings = home / "config.yaml"
    settings.write_text("model: user-model\nplugins:\n  enabled: [other]\n", encoding="utf-8")
    rules = home / "SOUL.md"
    rules.write_text("User rules", encoding="utf-8")
    for _ in range(2):
        assert main(["install", "--non-interactive", "--json", "--base-dir", str(base)]) == 0
        rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
        assert rows[-1]["complete"] is True
        assert rows[-1]["hook_verification"] == "local_plugin_readback"
        assert [r["stage"] for r in rows if r["status"] == "passed"] == [1, 2, 3]
    assert calls == [["doctor", "--backend-only"], "enable"] * 2
    assert (hook_install.target() / "__init__.py").read_text(encoding="utf-8") == hook_install.plugin_content(base)
    for removed in (1, 0):
        assert main(["uninstall", "--json"]) == 0
        assert json.loads(capsys.readouterr().out)["removed"] == removed
    assert settings.read_text(encoding="utf-8") == "model: user-model\nplugins:\n  enabled: [other]\n"
    assert rules.read_text(encoding="utf-8") == "User rules"
    assert base.exists()


@pytest.mark.parametrize("failure", ["missing-host", "backend", "foreign"])
def test_install_stops_without_changing_hooks(machine, monkeypatch, capsys, failure):
    home, base, calls = machine
    target = home / "plugins" / hook_install.NAME
    if failure == "missing-host":
        monkeypatch.setattr(install.shutil, "which", lambda _: None)
    elif failure == "backend":

        async def failed(_):
            return 1

        monkeypatch.setattr(install, "_command", failed)
    else:
        target.mkdir(parents=True)
        (target / "__init__.py").write_text("user code", encoding="utf-8")
    assert main(["install", "--non-interactive", "--json", "--base-dir", str(base)]) != 0
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["complete"] is False
    assert "enable" not in calls
    if failure == "foreign":
        assert (target / "__init__.py").read_text(encoding="utf-8") == "user code"
    else:
        assert not target.exists()


def test_uninstall_refuses_extra_files_and_respects_lock(machine):
    home, base, _ = machine
    target = hook_install.install(base)
    extra = target / "notes.txt"
    extra.write_text("user notes", encoding="utf-8")
    assert main(["uninstall"]) == 1
    assert extra.read_text(encoding="utf-8") == "user notes"
    lock = home / ".memu-hooks-lock"
    lock.mkdir(exist_ok=True)
    with workspace_lock(lock) as acquired:
        assert acquired
        assert main(["uninstall"]) == 2
    assert target.exists()


@pytest.mark.parametrize("location", ["plugins", "plugin", "manifest", "entry"])
def test_install_and_remove_refuse_symlinks(machine, location):
    home, base, _ = machine
    destination = hook_install.install(base)
    victim = {
        "plugins": home / "plugins",
        "plugin": destination,
        "manifest": destination / "plugin.yaml",
        "entry": destination / "__init__.py",
    }[location]
    original = victim.with_name(victim.name + "-original")
    victim.rename(original)
    try:
        victim.symlink_to(original, target_is_directory=original.is_dir())
    except OSError:
        original.rename(victim)
        pytest.skip("Symlink creation is unavailable")
    assert main(["install", "--non-interactive", "--json", "--base-dir", str(base)]) == 2
    assert main(["uninstall"]) == 1
    assert original.exists()


@pytest.mark.parametrize("entry", ["worker", "cli"])
def test_memory_entry_points_share_lock_and_cooldown(machine, monkeypatch, capsys, entry):
    from memu.hosts import host_cli

    _, base, _ = machine
    base.mkdir()
    calls = []

    async def pipeline(spec, args):
        calls.append(spec.host)
        with workspace_lock(base) as acquired:
            assert not acquired
        return 0

    monkeypatch.setattr(host_cli, "_run_hook_pipeline", pipeline)
    args = SimpleNamespace(base_dir=base, agent="hermes", log_path=base / "worker.log")

    def invoke():
        if entry == "worker":
            return hook.run_worker(args)
        return main(["hook-run", "--base-dir", str(base)])

    with workspace_lock(base) as acquired:
        assert acquired
        assert invoke() == 0
        assert calls == []
    assert invoke() == 0
    assert invoke() == 0
    assert calls == ["hermes"]
    output = args.log_path.read_text(encoding="utf-8") if entry == "worker" else capsys.readouterr().out
    assert "status=busy" in output
    assert "status=cooldown" in output
    assert "status=succeeded" in output


def test_plugin_maps_multimodal_events_and_ignores_own_runs(machine, monkeypatch):
    _, base, _ = machine
    path = hook_install.install(base) / "__init__.py"
    spec = importlib.util.spec_from_file_location("test_memu_hermes_plugin", path)
    plugin = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plugin)
    callbacks = {}
    plugin.register(SimpleNamespace(register_hook=lambda name, callback: callbacks.update({name: callback})))
    calls = []

    def call(action, event):
        calls.append((action, event))
        return {"context": "memory"}

    monkeypatch.setattr(plugin, "_call", call)
    pre, end = callbacks["pre_llm_call"], callbacks["on_session_end"]
    assert pre(user_message=[{"type": "image_url"}, {"type": "text", "text": "remember 中文"}], session_id="s") == {
        "context": "memory"
    }
    assert calls[-1] == ("retrieve", {"prompt": "remember 中文", "session_id": "s"})
    end(session_id="s", completed=False)
    assert len(calls) == 1
    end(session_id="s", completed=True)
    assert calls[-1] == ("memorize", {"session_id": "s"})
    assert pre(user_message="child", parent_session_id="s") is None
    monkeypatch.setenv("MEMU_BRIDGING_RUN", "1")
    assert pre(user_message="own", session_id="self") is None
    assert calls[-1] == ("remember-self", {"session_id": "self"})
    end(session_id="self", completed=True)
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_retrieval_returns_context_and_writes_log(tmp_path, monkeypatch):
    async def retrieve(query, **kwargs):
        assert query == "hello"
        return {"hits": [], "resources": []}

    monkeypatch.setattr(hook, "retrieve", retrieve)
    result = await hook.retrieve_context(tmp_path, {"prompt": "hello", "session_id": "s"})
    assert isinstance(result["context"], str)
    trace = json.loads(next((tmp_path / "log/hooks/retrieve").glob("*.json")).read_text(encoding="utf-8"))
    assert trace["session_id"] == "s"
    assert trace["status"] == "context_returned"


def test_launch_is_detached_and_binds_hermes_home(machine, monkeypatch):
    home, base, _ = machine
    captured = {}
    monkeypatch.setattr(hook.subprocess, "Popen", lambda argv, **kwargs: captured.update(argv=argv, **kwargs))
    log = hook.launch_background(base)
    assert log.exists()
    assert captured["env"]["HERMES_HOME"] == str(home)
    assert captured["stdin"] == hook.subprocess.DEVNULL
    assert "worker" in captured["argv"]


@pytest.mark.parametrize("name", ["INSTALL.md", "UNINSTALL.md"])
def test_guides_reject_old_cron_install_docs(name):
    assert not templates._valid_host_doc("hermes", name, "{{task_name}} {{former_task_names}} {{all_task_names}}")
