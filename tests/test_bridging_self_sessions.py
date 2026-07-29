"""The bridging run must not mine its own session (#606).

The record seam runs as a session of the host agent, logged where memU looks for
sessions, so without this the pipeline feeds on its own exhaust: prepare can
never report zero, and the newest transcripts on disk — memU's own bookkeeping —
take the max_jobs slots ahead of real conversation.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from memu.hosts.base import RecordKind, TranscriptSource
from memu.hosts.bridging import self_sessions
from memu.hosts.bridging.layout import Layout
from memu.hosts.bridging.transcripts import prepare_transcripts
from memu.hosts.claude_code.cli import SESSION_ID_ENV
from memu.hosts.claude_code.cli import SPEC as CLAUDE_CODE_SPEC
from memu.hosts.claude_code.sessions import ClaudeCodeTranscriptSource


class FakeSource(TranscriptSource):
    name = "fake"

    def __init__(self, root: pathlib.Path) -> None:
        self._root = root

    def root(self) -> pathlib.Path:
        return self._root

    def classify(self, record: str) -> RecordKind:
        return RecordKind.MESSAGE


def _session(root: pathlib.Path, name: str, turns: int, mtime: float) -> pathlib.Path:
    path = root / f"{name}.jsonl"
    path.write_text("".join(f'{{"role":"user","content":"turn {i}"}}\n' for i in range(turns)), encoding="utf-8")
    import os

    os.utime(path, (mtime, mtime))
    return path


# ── remembering ────────────────────────────────────────────────────────────────


def test_remembers_this_run_and_returns_everything_to_skip(tmp_path: pathlib.Path) -> None:
    store = tmp_path / ".self_sessions.fake.json"
    assert self_sessions.remember(store, "aaa") == ["aaa"]
    assert self_sessions.remember(store, "bbb") == ["aaa", "bbb"]
    assert json.loads(store.read_text(encoding="utf-8")) == ["aaa", "bbb"]


def test_remembering_the_same_session_twice_does_not_duplicate(tmp_path: pathlib.Path) -> None:
    """A retried bridging task, or a bare `prepare` the user runs by hand, is
    still the same host session."""
    store = tmp_path / ".self_sessions.fake.json"
    self_sessions.remember(store, "aaa")
    assert self_sessions.remember(store, "aaa") == ["aaa"]


def test_remembered_ids_are_capped_keeping_the_newest(tmp_path: pathlib.Path) -> None:
    store = tmp_path / ".self_sessions.fake.json"
    for i in range(self_sessions.MAX_REMEMBERED + 5):
        remembered = self_sessions.remember(store, f"s{i}")
    assert len(remembered) == self_sessions.MAX_REMEMBERED
    assert remembered[-1] == f"s{self_sessions.MAX_REMEMBERED + 4}"
    assert "s0" not in remembered


def test_load_fails_open_on_a_missing_or_corrupt_file(tmp_path: pathlib.Path) -> None:
    """Worst case is the pre-#606 behaviour, never a run that cannot start."""
    assert self_sessions.load(tmp_path / "nope.json") == []
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not json", encoding="utf-8")
    assert self_sessions.load(corrupt) == []
    wrong_shape = tmp_path / "wrong.json"
    wrong_shape.write_text('{"a": 1}', encoding="utf-8")
    assert self_sessions.load(wrong_shape) == []


# ── skipping ───────────────────────────────────────────────────────────────────


def test_own_session_is_skipped_and_does_not_end_the_scan(tmp_path: pathlib.Path) -> None:
    """The self-session is the *newest* file, so a `break` here would hide every
    real session underneath it — the whole point is that it is passed over."""
    logs = tmp_path / "logs"
    logs.mkdir()
    _session(logs, "real-old", turns=2, mtime=1000)
    _session(logs, "bridging-run", turns=9, mtime=3000)  # newest: this run's own
    source = FakeSource(logs)
    out = tmp_path / "out"
    manifest = tmp_path / "cursor.json"

    written = prepare_transcripts(
        source,
        out_dir=out,
        manifest_path=manifest,
        max_jobs=10,
        pending_path=tmp_path / "cursor.json.pending",
        skip_sessions=["bridging-run"],
    )

    assert written == 1
    staged = json.loads((tmp_path / "cursor.json.pending").read_text(encoding="utf-8"))
    assert list(staged) == ["real-old.jsonl"]
    assert "bridging-run.jsonl" not in staged


def test_without_the_skip_the_run_mines_itself(tmp_path: pathlib.Path) -> None:
    """The bug this closes: same tree, no skip list, and memU's own session is
    slotted first because it is the most recent."""
    logs = tmp_path / "logs"
    logs.mkdir()
    _session(logs, "real-old", turns=2, mtime=1000)
    _session(logs, "bridging-run", turns=9, mtime=3000)
    source = FakeSource(logs)

    written = prepare_transcripts(
        source,
        out_dir=tmp_path / "out",
        manifest_path=tmp_path / "cursor.json",
        max_jobs=10,
        pending_path=tmp_path / "cursor.json.pending",
    )

    assert written == 2
    assert "bridging-run.jsonl" in json.loads((tmp_path / "cursor.json.pending").read_text(encoding="utf-8"))


def test_skipping_frees_the_job_slots_for_real_sessions(tmp_path: pathlib.Path) -> None:
    """Self-sessions are newest-first, so unskipped they crowd out real work."""
    logs = tmp_path / "logs"
    logs.mkdir()
    for i in range(3):
        _session(logs, f"real-{i}", turns=2, mtime=1000 + i)
    own = [f"bridging-{i}" for i in range(3)]
    for i, name in enumerate(own):
        _session(logs, name, turns=4, mtime=5000 + i)
    source = FakeSource(logs)

    written = prepare_transcripts(
        source,
        out_dir=tmp_path / "out",
        manifest_path=tmp_path / "cursor.json",
        max_jobs=2,
        pending_path=tmp_path / "cursor.json.pending",
        skip_sessions=own,
    )

    assert written == 2
    staged = json.loads((tmp_path / "cursor.json.pending").read_text(encoding="utf-8"))
    assert set(staged) == {"real-2.jsonl", "real-1.jsonl"}


# ── only the scheduled run may claim a session ─────────────────────────────────


def test_a_hand_run_from_a_project_dir_is_not_a_bridging_run(tmp_path: pathlib.Path) -> None:
    """The regression this guards: running `prepare` by hand — during development,
    or to say "remember this conversation now" — must not permanently exclude the
    session it was run in. That would deliver the opposite of what was asked."""
    base = tmp_path / "memu" / "hosts" / "claude-code"
    project = tmp_path / "some" / "project"
    assert self_sessions.is_bridging_run(project, base, env={}) is False


def test_the_scheduled_workdir_is_a_bridging_run(tmp_path: pathlib.Path) -> None:
    """`schedule` passes -WorkingDirectory, so the task runs in memU's own tree.
    This keeps tasks registered before the env marker existed working."""
    base = tmp_path / "memu" / "hosts" / "claude-code"
    assert self_sessions.is_bridging_run(base, base, env={}) is True


def test_the_env_marker_wins_wherever_the_agent_wandered(tmp_path: pathlib.Path) -> None:
    """The wrapper exports it, so an agent that changes directory before running
    the command cannot lose the signal."""
    base = tmp_path / "memu" / "hosts" / "claude-code"
    elsewhere = tmp_path / "wherever"
    env = {self_sessions.BRIDGING_RUN_ENV: "1"}
    assert self_sessions.is_bridging_run(elsewhere, base, env=env) is True
    assert self_sessions.is_bridging_run(elsewhere, base, env={self_sessions.BRIDGING_RUN_ENV: "  "}) is False


def test_the_windows_wrapper_exports_the_marker() -> None:
    """Pins the wrapper to the constant, so renaming one without the other fails
    here rather than silently reopening #606."""
    from memu.hosts.scheduling.windows import wrapper_script

    script = wrapper_script(
        agent_path="C:/agents/claude.exe",
        schedule_command="claude -p {prompt}",
        prompt_file=pathlib.Path("C:/memu/bridge-prompt.txt"),
        log_file=pathlib.Path("C:/memu/bridge.log"),
        path_dirs=["C:/bin"],
    )
    assert f"$env:{self_sessions.BRIDGING_RUN_ENV} = '1'" in script


# ── the identity seam ──────────────────────────────────────────────────────────


def test_session_id_defaults_to_the_file_stem(tmp_path: pathlib.Path) -> None:
    """What the host reports in its environment has to line up with what we read
    back off a discovered session."""
    source = FakeSource(tmp_path)
    assert source.session_id(tmp_path / "6ea28aed-874f-44e1-9dd2-d8ad0b1bbc85.jsonl") == (
        "6ea28aed-874f-44e1-9dd2-d8ad0b1bbc85"
    )


def test_claude_code_attributes_a_subagent_transcript_to_its_parent(tmp_path: pathlib.Path) -> None:
    """Subagent transcripts sit one level deeper, in a directory named by the
    session that spawned them. A bridging run that spawns a subagent would
    otherwise leak the child's transcript into mining."""
    source = ClaudeCodeTranscriptSource(tmp_path)
    parent = "6ea28aed-874f-44e1-9dd2-d8ad0b1bbc85"
    top_level = tmp_path / "D--lab-proj" / f"{parent}.jsonl"
    subagent = tmp_path / "D--lab-proj" / parent / "b1c2d3e4-0000-4000-8000-000000000000.jsonl"

    assert source.session_id(top_level) == parent
    assert source.session_id(subagent) == parent


def test_claude_code_declares_its_session_id_variable() -> None:
    """Verified against claude-code 2.1.220: a headless `claude -p` run exports
    CLAUDE_CODE_SESSION_ID, and its value is the transcript's file name."""
    assert CLAUDE_CODE_SPEC.session_id_env == SESSION_ID_ENV == "CLAUDE_CODE_SESSION_ID"


def test_layout_scopes_the_file_per_host(tmp_path: pathlib.Path) -> None:
    """Two hosts' session ids are unrelated; a shared file would let one host's
    run id mask an unrelated real session on the other."""
    assert Layout(base=tmp_path, host="claude-code").self_sessions.name == ".self_sessions.claude-code.json"
    assert Layout(base=tmp_path, host="hermes").self_sessions.name == ".self_sessions.hermes.json"


@pytest.mark.parametrize("host_spec", [CLAUDE_CODE_SPEC])
def test_surveyed_hosts_keep_a_non_empty_variable(host_spec: object) -> None:
    """Guards the fan-out: a host listed here has been checked on a real install,
    so silently blanking the variable should fail rather than quietly restore the
    loop."""
    assert getattr(host_spec, "session_id_env", "")
