"""The inject seam's presentation: does the raw retrieval get reshaped for the agent?

``progressive_retrieve`` returns raw store records; :func:`_shape_for_agent` turns
them into the progressive form the standing instruction promises — files and
resources as *a location plus a summary*, segments naming their source. These pin
that contract: content gives way to a mirror ``path`` when the file is on disk,
survives inline when it is not, segments swap their UUID for that same path, and
resources collapse the duplicated url/local_path down to one ``path``.
"""

from __future__ import annotations

import pathlib

from memu.hosts import retrieval
from memu.hosts.bridging.recall_files import write_recall_file


def _result() -> dict:
    return {
        "segments": [
            {"id": "s1", "recall_file_id": "f1", "track": "memory", "text": "No sugar.", "score": 0.4},
            {"id": "s2", "recall_file_id": "gone", "track": "memory", "text": "orphan", "score": 0.3},
        ],
        "files": [
            {
                "id": "f1",
                "name": "coffee preferences",
                "track": "memory",
                "description": "How the user likes their coffee",
                "content": "No sugar.",
                "score": 0.4,
                "resource_urls": [],
            }
        ],
        "resources": [
            {"id": "r1", "url": "notes/onboarding.md", "local_path": "notes/onboarding.md", "caption": "notes"}
        ],
    }


def test_present_mirror_replaces_content_with_path(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "BASE_DIR", str(tmp_path))
    # The mirror file exists on disk (space in the name becomes a dash).
    write_recall_file(tmp_path, "memory", {"name": "coffee preferences", "description": "d", "content": "No sugar."})

    shaped = retrieval._shape_for_agent(_result())

    file = shaped["files"][0]
    assert "content" not in file, "a locatable file hands over a path, not its full text"
    assert "resource_urls" not in file, "the internal link list the instruction never names is dropped"
    assert file["path"] == str(tmp_path / "memory" / "coffee-preferences.md")


def test_missing_mirror_keeps_content_inline(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "BASE_DIR", str(tmp_path))
    # No file written: the mirror is gone, so the result must stay self-sufficient.
    shaped = retrieval._shape_for_agent(_result())

    file = shaped["files"][0]
    assert file["content"] == "No sugar.", "with no file to open, the text must survive inline"
    assert file["path"] == str(tmp_path / "memory" / "coffee-preferences.md")


def test_segment_source_file_points_at_its_files_path(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "BASE_DIR", str(tmp_path))
    shaped = retrieval._shape_for_agent(_result())

    seg = shaped["segments"][0]
    assert "recall_file_id" not in seg, "the internal UUID must not leak to the agent"
    assert seg["source_file"] == shaped["files"][0]["path"]
    # A segment whose file fell out of the result gets no fabricated path.
    assert shaped["segments"][1]["source_file"] is None


def test_resource_collapses_to_single_path(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "BASE_DIR", str(tmp_path))
    shaped = retrieval._shape_for_agent(_result())

    res = shaped["resources"][0]
    assert res["path"] == "notes/onboarding.md"
    assert "url" not in res and "local_path" not in res
