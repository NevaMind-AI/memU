from __future__ import annotations

import importlib.util
import json
import sys
import threading
from contextvars import ContextVar
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

    def plugin_command(*argv):
        calls.append(list(argv))
        if argv == ("--version",):
            return "Hermes Agent v0.23.1"
        if argv[:2] == ("config", "get"):
            return "true"
        if argv[:2] == ("plugins", "remove"):
            import shutil

            shutil.rmtree(hook_install.target())
        return ""

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
    hook_install.command("plugins", "enable", hook_install.NAME)


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


@pytest.mark.parametrize(
    "version, supported",
    [
        ("0.23.1", True),
        ("0.24.0", True),
        ("0.23.0", False),
        ("0.23.1-beta", False),
        ("2026.7.25", False),
        ("unknown", False),
    ],
)
def test_installer_requires_stable_async_host_support(machine, monkeypatch, capsys, version, supported):
    _, base, calls = machine
    command = hook_install.command
    monkeypatch.setattr(
        hook_install, "command", lambda *argv: f"Hermes Agent v{version}" if argv == ("--version",) else command(*argv)
    )
    code = main(["install", "--non-interactive", "--json", "--base-dir", str(base)])
    assert (code == 0) is supported
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    if not supported:
        assert "0.23.1" in rows[-1]["detail"]
        assert not hook_install.target().exists()
        assert ["doctor", "--backend-only"] not in calls


def test_installer_does_not_treat_python_or_sdk_version_as_hermes(machine, monkeypatch):
    monkeypatch.setattr(
        hook_install, "command", lambda *a: "Hermes Agent vgit.abcdef\nPython: 3.13.12\nOpenAI SDK: 2.8.0"
    )
    with pytest.raises(ValueError, match=r"0\.23\.1"):
        hook_install.check_version()


def test_install_rejects_unconfirmed_injection_grant(machine, monkeypatch, capsys):
    _, base, calls = machine
    command = hook_install.command
    monkeypatch.setattr(
        hook_install, "command", lambda *argv: "false" if argv[:2] == ("config", "get") else command(*argv)
    )
    assert main(["install", "--non-interactive", "--json", "--base-dir", str(base)]) == 1
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["complete"] is False
    assert ["plugins", "enable", hook_install.NAME] not in calls


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
        assert rows[-1]["hook_verification"] == "local_plugin_and_injection_grant_readback"
        assert [r["stage"] for r in rows if r["status"] == "passed"] == [1, 2, 3]
    assert (
        calls
        == [
            ["--version"],
            ["doctor", "--backend-only"],
            ["config", "set", hook_install.INJECTION_KEY, "true"],
            ["config", "get", hook_install.INJECTION_KEY, "--json"],
            ["plugins", "enable", hook_install.NAME],
        ]
        * 2
    )
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
    assert ["plugins", "enable", hook_install.NAME] not in calls
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


@pytest.fixture
def plugin(machine, monkeypatch):
    home, base, _ = machine
    path = hook_install.install(base) / "__init__.py"
    spec = importlib.util.spec_from_file_location("test_memu_hermes_plugin", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setitem(sys.modules, "hermes_constants", SimpleNamespace(get_hermes_home=lambda: home))
    return module


@pytest.fixture
def async_plugin(plugin, monkeypatch):
    route = ContextVar("hermes_session_key", default="route-s")
    monkeypatch.setitem(sys.modules, "hermes_cli.plugin_session", SimpleNamespace(session_key=route.get))
    jobs, deliveries, calls, callbacks = [], [], [], {}
    real_call = plugin._call

    def call(action, event):
        calls.append((action, event, route.get()))
        return {"context": "memory"} if action == "retrieve" else {}

    def thread(target, args, daemon):
        assert daemon
        return SimpleNamespace(start=lambda: jobs.append(lambda: target(*args)))

    def inject(message, *, session_key):
        deliveries.append((session_key, message))
        return True

    monkeypatch.setattr(plugin, "_call", call)
    monkeypatch.setattr(plugin.threading, "Thread", thread)
    ctx = SimpleNamespace(
        register_hook=lambda name, callback: callbacks.update({name: callback}), inject_message=inject
    )
    plugin.register(ctx)
    return SimpleNamespace(
        route=route, jobs=jobs, deliveries=deliveries, calls=calls, callbacks=callbacks, ctx=ctx, real_call=real_call
    )


@pytest.mark.parametrize("action", ["retrieve", "remember-self", "memorize"])
def test_plugin_isolates_its_python_for_all_actions(plugin, tmp_path, monkeypatch, action):
    poison = tmp_path / "foreign-python"
    poison.mkdir()
    (poison / "memu.py").write_text("raise RuntimeError('foreign Python dependency loaded')", encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", str(poison))
    monkeypatch.setenv("PYTHONHOME", str(poison))
    monkeypatch.setenv("MEMU_BRIDGING_RUN", "test-worker")
    run = plugin.subprocess.run

    def isolated_run(argv, **kwargs):
        assert "PYTHONPATH" not in kwargs["env"]
        assert "PYTHONHOME" not in kwargs["env"]
        assert kwargs["env"]["HERMES_HOME"] == str(hook_install.home())
        assert kwargs["env"]["MEMU_BRIDGING_RUN"] == "test-worker"
        if action == "memorize":
            # Exercise real command dispatch without launching a memory worker.
            bootstrap = (
                "from pathlib import Path; from memu.hosts.hermes import hook; "
                "hook.launch_background=lambda base: Path('not-started'); raise SystemExit(hook.main())"
            )
            argv = [argv[0], "-c", bootstrap, *argv[3:]]
        return run(argv, **kwargs)

    monkeypatch.setattr(plugin.subprocess, "run", isolated_run)
    result = plugin._call(action, {"prompt": "", "session_id": "test-worker"})
    expected = {"retrieve": {"context": None}, "remember-self": {}, "memorize": {"log_path": "not-started"}}
    assert result == expected[action]
    assert plugin.os.environ["PYTHONPATH"] == str(poison)
    assert plugin.os.environ["PYTHONHOME"] == str(poison)


def test_plugin_reports_subprocess_failure_in_hermes_logs(plugin, async_plugin, monkeypatch, caplog):
    monkeypatch.setattr(plugin, "_call", async_plugin.real_call)
    monkeypatch.setattr(
        plugin.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(returncode=1, stdout="", stderr="ModuleNotFoundError: startup dependency"),
    )
    assert async_plugin.callbacks["pre_llm_call"](user_message="hello", session_id="s") is None
    async_plugin.jobs.pop()()
    assert "memU retrieve exited 1" in caplog.text
    assert "ModuleNotFoundError: startup dependency" in caplog.text


def test_async_delivery_waits_for_continuation_before_memorizing(async_plugin, monkeypatch):
    bridge = async_plugin
    pre, end = bridge.callbacks["pre_llm_call"], bridge.callbacks["on_session_end"]
    assert pre(user_message=[{"type": "image_url"}, {"type": "text", "text": "remember 中文"}], session_id="s") is None
    assert bridge.calls == []
    end(session_id="s", completed=True)
    assert bridge.calls == []
    bridge.jobs.pop()()
    assert bridge.calls == [("retrieve", {"prompt": "remember 中文", "session_id": "s"}, "route-s")]
    route, message = bridge.deliveries.pop()
    assert route == "route-s" and "memory" in message
    end(session_id="s", completed=True)
    assert len(bridge.calls) == 1
    assert pre(user_message=message, session_id="s") is None
    assert bridge.jobs == []
    end(session_id="s", completed=False)
    assert len(bridge.calls) == 1
    end(session_id="s", completed=True)
    end(session_id="s", completed=True)
    assert bridge.calls[-1] == ("memorize", {"session_id": "s"}, "route-s")
    assert len(bridge.calls) == 2
    assert pre(user_message="child", parent_session_id="s") is None
    monkeypatch.setenv("MEMU_BRIDGING_RUN", "1")
    assert pre(user_message="own", session_id="self") is None
    assert bridge.calls[-1] == ("remember-self", {"session_id": "self"}, "route-s")
    end(session_id="self", completed=True)
    assert len(bridge.calls) == 3


@pytest.mark.parametrize("user_first", [False, True])
def test_async_delivery_preserves_user_input_merged_into_the_queue(async_plugin, user_first):
    bridge = async_plugin
    pre = bridge.callbacks["pre_llm_call"]
    pre(user_message="first question", session_id="s")
    bridge.jobs.pop()()
    delivered = bridge.deliveries[0][1]
    parts = ["new user input", delivered] if user_first else [delivered, "new user input"]
    pre(user_message="\n\n".join(parts), session_id="s")
    bridge.jobs.pop()()
    assert bridge.calls[-1] == ("retrieve", {"prompt": "new user input", "session_id": "s"}, "route-s")


def test_async_delivery_does_not_trust_unissued_markers(async_plugin):
    message = (
        "<!-- memu-hermes-retrieval:" + "a" * 32 + " -->\nmemory\n<!-- /memu-hermes-retrieval:" + "a" * 32 + " -->"
    )
    async_plugin.callbacks["pre_llm_call"](user_message=message, session_id="s")
    async_plugin.jobs.pop()()
    assert async_plugin.calls[0][1]["prompt"] == message


def test_failed_thread_start_does_not_block_memorization(plugin, async_plugin, monkeypatch):
    def start():
        raise RuntimeError("thread unavailable")  # noqa: TRY003

    monkeypatch.setattr(plugin.threading, "Thread", lambda **kwargs: SimpleNamespace(start=start))
    async_plugin.callbacks["pre_llm_call"](user_message="hello", session_id="s")
    async_plugin.callbacks["on_session_end"](session_id="s", completed=True)
    assert [action for action, _, _ in async_plugin.calls] == ["memorize"]


def test_async_delivery_supersedes_old_queries_and_turns(async_plugin):
    bridge = async_plugin
    pre, end = bridge.callbacks["pre_llm_call"], bridge.callbacks["on_session_end"]
    pre(user_message="old", session_id="s", turn_id="old")
    pre(user_message="new", session_id="s", turn_id="new")
    bridge.jobs.pop(0)()
    assert bridge.deliveries == []
    bridge.jobs.pop(0)()
    assert len(bridge.deliveries) == 1
    end(session_id="s", turn_id="old", completed=True)
    assert all(action != "memorize" for action, _, _ in bridge.calls)
    pre(user_message=bridge.deliveries[0][1], session_id="s", turn_id="continuation")
    end(session_id="s", turn_id="new", completed=True)
    assert all(action != "memorize" for action, _, _ in bridge.calls)
    end(session_id="s", turn_id="continuation", completed=True)
    assert bridge.calls[-1][0] == "memorize"


def test_async_delivery_keeps_session_routes_and_thread_context(async_plugin):
    bridge = async_plugin
    for sid in ("a", "b"):
        bridge.route.set(f"route-{sid}")
        bridge.callbacks["pre_llm_call"](user_message=sid, session_id=sid)
    bridge.route.set("different-ambient-session")
    for job in reversed(bridge.jobs):
        job()
    assert [route for route, _ in bridge.deliveries] == ["route-b", "route-a"]
    assert [route for _, _, route in bridge.calls] == ["route-b", "route-a"]


def test_async_delivery_drops_finalized_sessions(async_plugin):
    bridge = async_plugin
    bridge.callbacks["pre_llm_call"](user_message="hello", session_id="s")
    bridge.callbacks["on_session_finalize"](session_id="s")
    bridge.jobs.pop()()
    assert bridge.deliveries == []
    bridge.callbacks["on_session_end"](session_id="s", completed=True)
    assert all(action != "memorize" for action, _, _ in bridge.calls)


@pytest.mark.parametrize("failure", ["retrieval", "rejected", "empty"])
@pytest.mark.parametrize("ended_first", [False, True])
def test_failed_async_delivery_still_memorizes_successful_turns(
    plugin, async_plugin, monkeypatch, failure, ended_first
):
    bridge = async_plugin
    call = plugin._call

    def failed(action, event):
        if action == "retrieve":
            if failure == "retrieval":
                raise RuntimeError("test retrieval failed")  # noqa: TRY003
            if failure == "empty":
                return {"context": None}
        return call(action, event)

    monkeypatch.setattr(plugin, "_call", failed)
    if failure == "rejected":
        bridge.ctx.inject_message = lambda *a, **k: False
    bridge.callbacks["pre_llm_call"](user_message="hello", session_id="s")
    if ended_first:
        bridge.callbacks["on_session_end"](session_id="s", completed=True)
    bridge.jobs.pop()()
    if not ended_first:
        bridge.callbacks["on_session_end"](session_id="s", completed=True)
    assert sum(action == "memorize" for action, _, _ in bridge.calls) == 1


def test_async_delivery_requires_a_bound_route(async_plugin, caplog):
    async_plugin.route.set("")
    async_plugin.callbacks["pre_llm_call"](user_message="hello", session_id="s")
    assert async_plugin.jobs == []
    assert "session_key" in caplog.text


def test_retrieval_releases_hook_before_background_work_finishes(plugin, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    entered, release, delivered = threading.Event(), threading.Event(), threading.Event()
    monkeypatch.setitem(sys.modules, "hermes_cli.plugin_session", SimpleNamespace(session_key=lambda: "route-s"))

    def call(action, event):
        entered.set()
        assert release.wait(5)
        return {"context": "memory"}

    monkeypatch.setattr(plugin, "_call", call)
    callbacks = {}
    plugin.register(
        SimpleNamespace(
            register_hook=lambda name, callback: callbacks.update({name: callback}),
            inject_message=lambda *a, **k: delivered.set() or True,
        )
    )
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(callbacks["pre_llm_call"], user_message="hello", session_id="s")
        try:
            assert entered.wait(2)
            assert future.result(timeout=1) is None
            assert not delivered.is_set()
        finally:
            release.set()
        assert delivered.wait(2)


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
@pytest.mark.parametrize("marker", ["", "<!-- memu-hermes-install: plugin-v1 -->"])
def test_guides_reject_older_install_docs(name, marker):
    assert not templates._valid_host_doc(
        "hermes", name, marker + "{{task_name}} {{former_task_names}} {{all_task_names}}"
    )
