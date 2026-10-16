"""Hook mode (ADR 0020): installers edit only their own entry, and a hook run
does prepare and commit itself, leaving the agent nothing but the job files."""

from __future__ import annotations

import json
import pathlib
import sys
import textwrap
import tomllib
from typing import Any

import pytest

from memu.hosts.base import RecordKind, TranscriptSource
from memu.hosts.bridging import Layout, self_sessions
from memu.hosts.codex.sessions import CodexTranscriptSource
from memu.hosts.hooks import CodexNotifyHook, HeadlessAgent, HookSpec, codex_thread_id, runner
from memu.hosts.hooks.installers import HookConfigError
from memu.hosts.host_cli import HostSpec, run


@pytest.fixture()
def layout(tmp_path: pathlib.Path) -> Layout:
    return Layout.default(host="fake", base=tmp_path / "memu")


# ---------------------------------------------------------------------------
# Codex: config.toml notify
# ---------------------------------------------------------------------------

CODEX_CONFIG = textwrap.dedent(
    """\
    # my codex config
    model = "gpt-5"

    [tui]
    notify = true

    [mcp_servers.docs]
    command = "docs-mcp"
    """
)


def test_codex_install_prepends_a_top_level_key_and_preserves_the_rest(tmp_path: pathlib.Path, layout: Layout) -> None:
    config = tmp_path / "config.toml"
    config.write_text(CODEX_CONFIG)
    hook = CodexNotifyHook(config)

    assert hook.install(["/bin/memu-codex", "hook", "--min-interval", "30"], layout)
    assert not hook.install(["/bin/memu-codex", "hook", "--min-interval", "30"], layout)

    text = config.read_text()
    assert text.endswith(CODEX_CONFIG)
    parsed = tomllib.loads(text)
    assert parsed["notify"] == ["/bin/memu-codex", "hook", "--min-interval", "30"]
    assert parsed["tui"] == {"notify": True}
    assert hook.installed("memu-codex")

    assert hook.remove("memu-codex", layout)
    assert config.read_text() == CODEX_CONFIG


def test_codex_install_chains_and_remove_restores_an_existing_notify(tmp_path: pathlib.Path, layout: Layout) -> None:
    config = tmp_path / "config.toml"
    config.write_text('notify = [\n  "node",\n  "/home/u/.heyboss/codex-notify.mjs",\n]  # heyboss\n' + CODEX_CONFIG)
    hook = CodexNotifyHook(config)

    hook.install(["memu-codex", "hook"], layout)

    assert tomllib.loads(config.read_text())["notify"] == ["memu-codex", "hook"]
    chain = json.loads((layout.base / CodexNotifyHook.CHAIN_FILE).read_text())
    assert chain == ["node", "/home/u/.heyboss/codex-notify.mjs"]

    hook.remove("memu-codex", layout)

    assert tomllib.loads(config.read_text())["notify"] == ["node", "/home/u/.heyboss/codex-notify.mjs"]
    assert not (layout.base / CodexNotifyHook.CHAIN_FILE).exists()


def test_codex_forward_passes_the_payload_to_the_displaced_notify(tmp_path: pathlib.Path, layout: Layout) -> None:
    out = tmp_path / "forwarded.json"
    script = tmp_path / "notify.py"
    script.write_text(f"import sys, json, pathlib\npathlib.Path({str(out)!r}).write_text(json.dumps(sys.argv[1:]))\n")
    layout.base.mkdir(parents=True)
    (layout.base / CodexNotifyHook.CHAIN_FILE).write_text(json.dumps([sys.executable, str(script)]))

    CodexNotifyHook(tmp_path / "config.toml").forward(layout, ['{"type":"agent-turn-complete"}'])

    import time

    for _ in range(100):
        if out.exists():
            break
        time.sleep(0.05)
    assert json.loads(out.read_text()) == ['{"type":"agent-turn-complete"}']


def test_codex_refuses_a_file_it_cannot_parse(tmp_path: pathlib.Path, layout: Layout) -> None:
    config = tmp_path / "config.toml"
    config.write_text("notify = [unclosed\n")

    with pytest.raises(HookConfigError):
        CodexNotifyHook(config).install(["memu-codex", "hook"], layout)
    assert config.read_text() == "notify = [unclosed\n"


def test_codex_thread_id_matches_the_rollout_file_name(tmp_path: pathlib.Path) -> None:
    thread = "0199a213-81c0-7800-8aa1-bbab2a035a53"
    stdout = '{"type":"thread.started","thread_id":"' + thread + '"}\n{"type":"turn.started"}\n'
    rollout = tmp_path / "2026" / "10" / "01" / f"rollout-2026-10-01T10-00-00-{thread}.jsonl"

    assert codex_thread_id(stdout) == thread
    assert codex_thread_id("not json\n") is None
    assert CodexTranscriptSource(tmp_path).session_id(rollout) == thread


# ---------------------------------------------------------------------------
# hook-run end to end, with a fake agent and a fake store
# ---------------------------------------------------------------------------


class FakeSource(TranscriptSource):
    name = "fake"

    def __init__(self, root: str | pathlib.Path) -> None:
        self._root = pathlib.Path(root)

    def root(self) -> pathlib.Path:
        return self._root

    def classify(self, record: str) -> RecordKind:
        return RecordKind.MESSAGE


class FakeService:
    def __init__(self) -> None:
        self.committed: list[dict[str, Any]] = []

    async def list_all_recall_files(
        self, where: Any = None, *, cursor: str | None = None, limit: int = 100
    ) -> dict[str, Any]:
        return {"recall_files": [], "next_cursor": None}

    async def commit_results(self, recall_files: Any, resource: Any) -> dict[str, Any]:
        self.committed.append({"recall_files": recall_files, "resource": resource})
        return {"recall_files": recall_files, "resources": resource}


FAKE_AGENT = """\
import json, os, pathlib, sys
prompt = sys.stdin.read()
base = pathlib.Path.cwd()
(base / "agent-run.json").write_text(json.dumps({
    "argv": sys.argv[1:], "prompt": prompt, "bridging": os.environ.get("MEMU_BRIDGING_RUN"),
    "jobs": sorted(p.name for p in (base / "jobs").glob("*.txt")),
}))
(base / "memory").mkdir(exist_ok=True)
(base / "memory" / "learned.md").write_text("---\\nname: learned\\ndescription: d\\n---\\nbody\\n")
sys.exit(int(os.environ.get("FAKE_AGENT_EXIT", "0")))
"""


@pytest.fixture()
def rig(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> tuple[HostSpec, Layout, FakeService]:
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "s1.jsonl").write_text('{"role":"user","content":"hi"}\n{"role":"assistant","content":"yo"}\n')
    script = tmp_path / "agent.py"
    script.write_text(FAKE_AGENT)

    service = FakeService()
    import memu.hosts.bridging.pipeline as pipeline

    monkeypatch.setattr(pipeline, "build_agentic_memory_backend_from_env", lambda: service)
    monkeypatch.delenv(self_sessions.BRIDGING_RUN_ENV, raising=False)
    spec = HostSpec(
        host="fake",
        display="Fake",
        package="memu.hosts.codex",
        task_name="memu-bridging-fake",
        source_factory=FakeSource,
        session_dir=str(logs),
        session_help="fake log",
        instruction_path=str(tmp_path / "AGENTS.md"),
        hook=HookSpec(
            agent=HeadlessAgent(argv=(sys.executable, str(script), "{session_id}"), preset_session_id=True),
            installer=CodexNotifyHook(tmp_path / "config.toml"),
        ),
    )
    return spec, Layout.default(host="fake", base=tmp_path / "memu"), service


def _hook_run(spec: HostSpec, layout: Layout, *extra: str) -> int:
    return run(spec, ["hook-run", "--base-dir", str(layout.base), *extra])


def test_hook_run_prepares_runs_the_agent_and_commits(rig) -> None:
    spec, layout, service = rig

    assert _hook_run(spec, layout) == 0

    agent_run = json.loads((layout.base / "agent-run.json").read_text())
    assert agent_run["bridging"] == "1", "the agent's own hook must be able to stand down"
    assert agent_run["jobs"], "prepare ran before the agent"
    assert "commit" in agent_run["prompt"] and str(layout.jobs) in agent_run["prompt"]
    assert [f["name"] for f in service.committed[-1]["recall_files"]] == ["learned"]
    assert layout.session_manifest.exists(), "commit promoted the cursor"
    assert not list(layout.jobs.glob("*.txt"))
    # The run's own session was claimed before it could ever be mined.
    assert agent_run["argv"][0] in self_sessions.load(layout.self_sessions)


def test_a_failed_agent_leaves_jobs_and_cursor_for_the_next_run(rig, monkeypatch: pytest.MonkeyPatch) -> None:
    spec, layout, service = rig
    monkeypatch.setenv("FAKE_AGENT_EXIT", "3")

    assert _hook_run(spec, layout) == 1
    assert list(layout.jobs.glob("*.txt")), "jobs stay on disk"
    assert not layout.session_manifest.exists(), "the cursor did not advance"
    assert not service.committed

    monkeypatch.setenv("FAKE_AGENT_EXIT", "0")
    assert _hook_run(spec, layout) == 0
    assert service.committed[0]["recall_files"], "the leftovers were committed first"
    assert layout.session_manifest.exists()


def test_hook_run_stands_down_while_another_holds_the_lock(rig) -> None:
    spec, layout, service = rig
    with runner.run_lock(layout) as held:
        assert held
        assert _hook_run(spec, layout) == 0
    assert not service.committed
    assert layout.hook_rerun.exists(), "the run in flight is asked to go again"


def test_hook_run_respects_the_cooldown(rig) -> None:
    spec, layout, service = rig
    assert _hook_run(spec, layout, "--min-interval", "30") == 0
    committed = len(service.committed)

    assert _hook_run(spec, layout, "--min-interval", "30") == 0
    assert len(service.committed) == committed


def test_hook_inside_a_bridging_run_does_nothing(rig, monkeypatch: pytest.MonkeyPatch) -> None:
    spec, layout, _ = rig
    monkeypatch.setenv(self_sessions.BRIDGING_RUN_ENV, "1")
    spawned: list[Any] = []
    monkeypatch.setattr(runner, "spawn_detached", lambda argv, lay: spawned.append(argv))

    assert run(spec, ["hook", "--base-dir", str(layout.base), "{}"]) == 0
    assert not spawned


def test_hook_spawns_hook_run_detached(rig, monkeypatch: pytest.MonkeyPatch) -> None:
    spec, layout, _ = rig
    spawned: list[list[str]] = []
    monkeypatch.setattr(runner, "spawn_detached", lambda argv, lay: spawned.append(list(argv)))

    assert run(spec, ["hook", "--base-dir", str(layout.base), "--min-interval", "30", '{"type":"x"}']) == 0
    assert spawned == [
        [
            sys.executable,
            "-m",
            "memu.hosts.codex.cli",
            "hook-run",
            "--base-dir",
            str(layout.base),
            "--min-interval",
            "30",
        ]
    ]


def test_install_hook_pins_the_agent_path(rig, tmp_path: pathlib.Path) -> None:
    spec, layout, _ = rig
    assert run(spec, ["install-hook", "--base-dir", str(layout.base)]) == 0
    assert spec.hook is not None
    assert spec.hook.installer.installed("memu-fake")
    notify = tomllib.loads((tmp_path / "config.toml").read_text())["notify"]
    assert notify[-2:] == ["--agent", sys.executable]
    assert run(spec, ["remove-hook", "--base-dir", str(layout.base)]) == 0
    assert not spec.hook.installer.installed("memu-fake")


@pytest.mark.parametrize("failure", ["missing", "broken"])
def test_install_hook_rejects_unusable_cli_without_changing_config(rig, monkeypatch, failure: str) -> None:
    import shutil
    import subprocess

    spec, layout, _ = rig
    assert spec.hook is not None
    config = spec.hook.installer.path
    config.write_text('model = "keep"\n', encoding="utf-8")
    before = config.read_bytes()
    if failure == "missing":
        monkeypatch.setattr(shutil, "which", lambda binary: None)
    else:

        def fail(*args, **kwargs):
            raise subprocess.CalledProcessError(1, [sys.executable, "--version"])

        monkeypatch.setattr(subprocess, "run", fail)

    assert run(spec, ["install-hook", "--base-dir", str(layout.base)]) == 1
    assert config.read_bytes() == before


def test_codex_install_uses_notify_without_a_scheduled_task() -> None:
    from importlib.resources import files

    doc = (files("memu.hosts.codex") / "INSTALL.md").read_text(encoding="utf-8")
    normalized = " ".join(doc.replace("**", "").split())

    assert "memu-codex install-hook" in normalized
    assert "no scheduled task" in normalized
    assert "Remove a scheduled bridging" not in normalized
    assert "approval and sandbox bypass" in normalized
