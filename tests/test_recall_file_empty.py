from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from memu.app.memorize.lifecycle import MemorizeWorkspace, commit_memorize
from memu.hosts.bridging import Layout, pipeline
from memu.hosts.bridging.instructions import prepare_instruction_jobs
from memu.hosts.bridging.manifest import snapshot_tracked
from memu.hosts.bridging.recall_files import read_recall_file


@pytest.mark.parametrize("body", ["", " \n\t"])
@pytest.mark.parametrize(
    "marker", ["", "empty: false\n", "empty: yes\n", 'empty: "true"\n', "empty: true\nempty: true\n"]
)
def test_empty_memory_requires_one_explicit_acknowledgement(tmp_path: Path, marker: str, body: str) -> None:
    path = tmp_path / "note.md"
    text = f"---\nname: note\ndescription: keep\n{marker}---\n{body}"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="requires empty: true"):
        read_recall_file(path, "memory")
    assert path.read_text(encoding="utf-8") == text
    assert read_recall_file(path, "skill")["content"] == body


@pytest.mark.parametrize("body", ["", " \n\t", "restored fact"])
def test_empty_acknowledgement_is_local_metadata(tmp_path: Path, body: str) -> None:
    path = tmp_path / "note.md"
    path.write_text(f"---\nname: note\ndescription: keep\nempty: true\n---\n{body}", encoding="utf-8")
    assert read_recall_file(path, "memory") == {
        "name": "note",
        "description": "keep",
        "track": "memory",
        "content": body,
    }


@pytest.mark.parametrize("entrypoint", ["bridging", "memorize"])
async def test_empty_transition_and_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entrypoint: str) -> None:
    layout = Layout.default(host="fake", base=tmp_path / "workspace")
    workspace = MemorizeWorkspace(layout.base)
    layout.memory.mkdir(parents=True)
    path = layout.memory / "note.md"
    header = "---\nname: note\ndescription: keep\n"
    path.write_text(header + "---\noriginal fact", encoding="utf-8")
    manifest = layout.memory_manifest if entrypoint == "bridging" else workspace.manifest
    snapshot_tracked(layout.base, layout.track_dirs, manifest)
    marker = layout.session_manifest_pending if entrypoint == "bridging" else workspace.active_run
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text('{"schema_version":"1.0"}\n', encoding="utf-8")
    backend = AsyncMock()
    backend.commit_results.return_value = {"recall_files": [], "resources": []}
    monkeypatch.setattr(pipeline, "build_agentic_memory_backend_from_env", lambda: backend)

    async def submit() -> None:
        if entrypoint == "bridging":
            await pipeline.commit(layout)
        else:
            await commit_memorize(workspace, backend)

    original_manifest = manifest.read_bytes()
    original_marker = marker.read_bytes()
    path.write_text(header + "---\n \t\n", encoding="utf-8")
    with pytest.raises(ValueError, match="requires empty: true"):
        await submit()
    backend.commit_results.assert_not_awaited()
    assert manifest.read_bytes() == original_manifest
    assert marker.read_bytes() == original_marker
    assert path.exists()

    # A restored body wins over the old acknowledgement. Failure retains retry state.
    restored = header + "empty: true\n---\nrestored fact\nempty: keep this body line"
    path.write_text(restored, encoding="utf-8")
    backend.commit_results.side_effect = RuntimeError("backend failed")
    with pytest.raises(RuntimeError, match="backend failed"):
        await submit()
    assert path.read_text(encoding="utf-8") == restored
    assert manifest.read_bytes() == original_manifest
    assert marker.read_bytes() == original_marker

    backend.commit_results.side_effect = None
    await submit()
    assert path.read_text(encoding="utf-8") == header + "---\nrestored fact\nempty: keep this body line"
    payload = backend.commit_results.await_args.kwargs["recall_files"][0]
    assert payload["content"] == "restored fact\nempty: keep this body line"
    assert "empty" not in payload
    assert json.loads(manifest.read_text(encoding="utf-8"))

    # Successful restoration consumes the marker; a later accidental blank is rejected again.
    marker.write_bytes(original_marker)
    backend.commit_results.reset_mock()
    path.write_text(header + "---\n", encoding="utf-8")
    with pytest.raises(ValueError, match="requires empty: true"):
        await submit()
    backend.commit_results.assert_not_awaited()

    path.write_text(header + "empty: true\n---\n", encoding="utf-8")
    await submit()
    assert not path.exists()
    assert not json.loads(manifest.read_text(encoding="utf-8"))
    assert backend.commit_results.await_args.kwargs["recall_files"][0]["content"] == ""


def test_custom_memory_jobs_include_empty_submission_contract(tmp_path: Path) -> None:
    prepare_instruction_jobs(
        tmp_path / "jobs",
        tmp_path / "sessions",
        tmp_path / "memory",
        tmp_path / "skill",
        tmp_path / "resource-log",
        1,
        memory_template="Custom {input_path} {track_dir}",
    )
    job = (tmp_path / "jobs/1.txt").read_text(encoding="utf-8")
    assert job.startswith("Custom ")
    assert "`empty: true`" in job
    assert "non-empty body restores normal memory automatically" in job
    assert "## Empty memory submissions" not in (tmp_path / "jobs/2.txt").read_text(encoding="utf-8")
