"""State advances on durable success, not on intent (#518).

The session cursor is staged by ``prepare`` and promoted only by a successful
``commit``; the memory snapshot is bootstrapped once and re-taken only by a
successful ``commit``. These pin the four behaviors that make the pipeline
at-least-once instead of at-most-once: a bare prepare is harmless, a repeated
prepare re-offers the same sessions, a completed cycle advances exactly once,
and files written by a run that died before commit stay committable.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest

from memu.hosts.base import RecordKind, TranscriptSource
from memu.hosts.bridging import Layout, commit, prepare


class FakeSource(TranscriptSource):
    name = "fake"

    def __init__(self, root: pathlib.Path) -> None:
        self._root = root

    def root(self) -> pathlib.Path:
        return self._root

    def classify(self, record: str) -> RecordKind:
        return RecordKind.MESSAGE


class FakeService:
    """Stands in for the store: records commits, serves an empty mirror."""

    def __init__(self) -> None:
        self.committed: list[dict[str, Any]] = []

    async def list_all_recall_files(
        self, where: Any = None, *, cursor: str | None = None, limit: int = 100
    ) -> dict[str, Any]:
        return {"recall_files": [], "next_cursor": None}

    async def commit_results(self, recall_files: Any, resource: Any) -> dict[str, Any]:
        self.committed.append({"recall_files": recall_files, "resource": resource})
        return {"recall_files": recall_files, "resources": resource}


@pytest.fixture(params=[False, True], ids=["shared-workspace", "separate-state"])
def rig(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> tuple[FakeSource, Layout, FakeService]:
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "s1.jsonl").write_text('{"role":"user","content":"hi"}\n{"role":"assistant","content":"yo"}\n')

    layout = Layout(
        base=tmp_path / "memu",
        host="fake",
        state_base=tmp_path / "state" if request.param else None,
    )
    service = FakeService()
    import memu.hosts.bridging.pipeline as pipeline

    monkeypatch.setattr(pipeline, "build_agentic_memory_backend_from_env", lambda: service)
    return FakeSource(logs), layout, service


@pytest.mark.parametrize("tracks", [(), ("memory",), ("skill",), ("memory", "skill")])
async def test_prepare_initializes_tracks_after_mirroring(rig, monkeypatch, tracks) -> None:
    from unittest.mock import AsyncMock

    import memu.hosts.bridging.pipeline as pipeline

    source, layout, service = rig
    pages = [
        {
            "recall_files": [{"name": f"test-{track}", "track": track, "description": "existing", "content": track}],
            "next_cursor": str(index + 1) if index + 1 < len(tracks) else None,
        }
        for index, track in enumerate(tracks)
    ] or [{"recall_files": [], "next_cursor": None}]
    listing = AsyncMock(side_effect=pages)
    monkeypatch.setattr(service, "list_all_recall_files", listing)
    monkeypatch.setattr(pipeline.templates, "resolve", lambda _key, fallback: fallback)

    assert await prepare(source, layout, verify_command="x verify-resources") == 1

    for track in ("memory", "skill"):
        directory = layout.base / track
        files = list(directory.iterdir())
        assert len(files) == (1 if track in tracks else 0)
        if files:
            assert files[0].read_text(encoding="utf-8") == (
                f"---\nname: test-{track}\ndescription: existing\n---\n{track}"
            )
    assert [call.kwargs["cursor"] for call in listing.await_args_list] == [
        None,
        *[str(index) for index in range(1, len(pages))],
    ]
    assert len(list(layout.jobs.glob("*.txt"))) == 3

    await commit(layout)

    assert service.committed == [{"recall_files": [], "resource": []}]
    assert layout.session_manifest.exists()
    assert not layout.session_manifest_pending.exists()
    assert list(layout.jobs.glob("*.txt")) == []
    assert list(layout.sessions.glob("*.jsonl")) == []


async def test_bare_prepare_leaves_the_promoted_cursor_untouched(rig) -> None:
    source, layout, _ = rig

    n = await prepare(source, layout, verify_command="x verify-resources")

    assert n == 1
    assert not layout.session_manifest.exists(), "prepare must not advance the durable cursor"
    assert layout.session_manifest_pending.exists(), "the advanced cursor is staged, not promoted"


async def test_repeated_prepare_reoffers_the_same_sessions(rig) -> None:
    source, layout, _ = rig

    first = await prepare(source, layout, verify_command="x verify-resources")
    second = await prepare(source, layout, verify_command="x verify-resources")

    assert (first, second) == (1, 1), "an uncommitted batch must stay selectable"


async def test_commit_promotes_the_cursor_exactly_once(rig) -> None:
    source, layout, _ = rig

    await prepare(source, layout, verify_command="x verify-resources")
    await commit(layout)

    assert layout.session_manifest.exists()
    assert not layout.session_manifest_pending.exists()
    assert json.loads(layout.session_manifest.read_text())["s1.jsonl"]["lines"] == 2

    assert await prepare(source, layout, verify_command="x verify-resources") == 0, "after promotion the batch is spent"


async def test_files_from_a_died_run_stay_committable(rig) -> None:
    """The crash scenario: run 1 prepares and writes a memory file but never
    commits; run 2's prepare must not absorb that file into the baseline, and
    run 2's commit must submit it."""
    source, layout, service = rig

    await prepare(source, layout, verify_command="x verify-resources")
    layout.memory.mkdir(parents=True, exist_ok=True)
    (layout.memory / "orphan.md").write_text("---\nname: orphan\n---\nmined but never committed\n")
    # run 1 dies here — no commit

    await prepare(source, layout, verify_command="x verify-resources")  # run 2
    await commit(layout)

    submitted = [f["name"] for f in service.committed[0]["recall_files"]]
    assert "orphan" in submitted


async def test_commit_clears_this_runs_working_files(rig) -> None:
    """A durable commit wipes the ephemeral working dirs, so the next run's
    LEFTOVERS step re-processes nothing that was already committed."""
    source, layout, _ = rig

    await prepare(source, layout, verify_command="x verify-resources")
    assert list(layout.jobs.glob("*.txt")), "prepare should have written job files"
    assert list(layout.sessions.glob("*.jsonl")), "prepare should have written session slices"

    await commit(layout)

    assert list(layout.jobs.glob("*.txt")) == [], "commit must clear the job instructions"
    assert list(layout.sessions.glob("*.jsonl")) == [], "commit must clear the session slices"
    assert not layout.resource_log.exists(), "commit must clear the touched-file log"


async def test_prepare_skips_the_resource_job_when_no_new_sessions(rig) -> None:
    """No sessions means no skill jobs to populate the touched-file log, so the
    resource-describe job has nothing to do and is not written at all."""
    source, layout, _ = rig

    await prepare(source, layout, verify_command="x verify-resources")
    await commit(layout)  # spend the batch

    n = await prepare(source, layout, verify_command="x verify-resources")

    assert n == 0
    assert list(layout.jobs.glob("*.txt")) == [], "a no-new-session prepare writes no jobs at all"


async def test_snapshot_is_retaken_at_commit_so_reruns_are_clean(rig) -> None:
    source, layout, service = rig

    await prepare(source, layout, verify_command="x verify-resources")
    layout.memory.mkdir(parents=True, exist_ok=True)
    (layout.memory / "note.md").write_text("---\nname: note\n---\nv1\n")
    await commit(layout)

    await commit(layout)  # nothing changed since the last commit

    assert [f["name"] for f in service.committed[0]["recall_files"]] == ["note"]
    assert service.committed[1]["recall_files"] == [], "the post-commit snapshot must absorb committed work"


async def test_separate_workspaces_share_progress_but_not_working_files(rig) -> None:
    source, original, service = rig
    first = Layout(original.base / "runs" / "A", original.host, state_base=original.state)
    second = Layout(original.base / "runs" / "B", original.host, state_base=original.state)
    assert first.session_manifest == second.session_manifest == original.session_manifest
    assert first.self_sessions == second.self_sessions == original.self_sessions
    for layout in (first, second):
        assert await prepare(source, layout, verify_command="unused") == 1
        assert all(
            path.parent == layout.base
            for path in (
                layout.sessions,
                layout.jobs,
                layout.memory,
                layout.skill,
                layout.memory_manifest,
                layout.session_manifest_pending,
                layout.run_marker,
                layout.resource_log,
                layout.resources,
            )
        )

    # Independent files do not claim input: both prepares still observe the old
    # promoted cursor. The caller must serialize the complete cycle.
    assert first.session_manifest_pending.read_bytes() == second.session_manifest_pending.read_bytes()
    assert (first.sessions / "1.jsonl").read_bytes() == (second.sessions / "1.jsonl").read_bytes()
    assert not first.session_manifest.exists()
    (first.memory / "A.md").write_text("---\nname: A\n---\nfirst run\n", encoding="utf-8")
    (second.memory / "B.md").write_text("---\nname: B\n---\nsecond run\n", encoding="utf-8")
    second.resource_log.write_text("second run log\n", encoding="utf-8")
    before = {path.relative_to(second.base): path.read_bytes() for path in second.base.rglob("*") if path.is_file()}

    await commit(first)

    assert [file["name"] for file in service.committed[0]["recall_files"]] == ["A"]
    assert json.loads(first.session_manifest.read_text())["s1.jsonl"]["lines"] == 2
    assert not first.session_manifest_pending.exists()
    assert not list(first.sessions.iterdir()) and not list(first.jobs.iterdir())
    assert before == {
        path.relative_to(second.base): path.read_bytes() for path in second.base.rglob("*") if path.is_file()
    }
    # A fresh workspace reads the successful run's promoted cursor.
    third = Layout(original.base / "runs" / "C", original.host, state_base=original.state)
    assert await prepare(source, third, verify_command="unused") == 0
    assert not list(third.jobs.iterdir())


async def test_failed_commit_preserves_cursor_and_run_for_retry(rig, monkeypatch) -> None:
    from unittest.mock import AsyncMock

    source, layout, service = rig
    await prepare(source, layout, verify_command="unused")
    await commit(layout)
    cursor = layout.session_manifest.read_bytes()
    with (source.root() / "s1.jsonl").open("a", encoding="utf-8") as stream:
        stream.write('{"role":"user","content":"new turn"}\n')
    await prepare(source, layout, verify_command="unused")
    (layout.memory / "retry.md").write_text("---\nname: retry\n---\nretained\n", encoding="utf-8")
    baseline = layout.memory_manifest.read_bytes()
    pending = layout.session_manifest_pending.read_bytes()
    with monkeypatch.context() as patch:
        patch.setattr(service, "commit_results", AsyncMock(side_effect=RuntimeError("synthetic failure")))
        with pytest.raises(RuntimeError, match="synthetic failure"):
            await commit(layout)
    assert layout.session_manifest.read_bytes() == cursor
    assert layout.session_manifest_pending.read_bytes() == pending
    assert layout.memory_manifest.read_bytes() == baseline
    assert list(layout.jobs.iterdir()) and list(layout.sessions.iterdir())

    await commit(layout)
    assert layout.session_manifest.read_bytes() == pending
    assert [file["name"] for file in service.committed[-1]["recall_files"]] == ["retry"]
