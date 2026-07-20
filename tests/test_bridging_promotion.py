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

    async def list_all_recall_files(self) -> dict[str, Any]:
        return {"categories": []}

    async def commit_results(self, recall_files: Any, resource: Any) -> dict[str, Any]:
        self.committed.append({"recall_files": recall_files, "resource": resource})
        return {"recall_files": recall_files, "resources": resource}


@pytest.fixture()
def rig(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> tuple[FakeSource, Layout, FakeService]:
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "s1.jsonl").write_text('{"role":"user","content":"hi"}\n{"role":"assistant","content":"yo"}\n')

    layout = Layout.default(host="fake", base=tmp_path / "memu")
    service = FakeService()
    import memu.hosts.bridging.pipeline as pipeline

    monkeypatch.setattr(pipeline, "build_service_from_env", lambda: service)
    return FakeSource(logs), layout, service


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


async def test_snapshot_is_retaken_at_commit_so_reruns_are_clean(rig) -> None:
    source, layout, service = rig

    await prepare(source, layout, verify_command="x verify-resources")
    layout.memory.mkdir(parents=True, exist_ok=True)
    (layout.memory / "note.md").write_text("---\nname: note\n---\nv1\n")
    await commit(layout)

    await commit(layout)  # nothing changed since the last commit

    assert [f["name"] for f in service.committed[0]["recall_files"]] == ["note"]
    assert service.committed[1]["recall_files"] == [], "the post-commit snapshot must absorb committed work"
