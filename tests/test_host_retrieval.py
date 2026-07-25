"""The inject seam's presentation: does the raw retrieval get reshaped for the agent?

``progressive_retrieve`` returns raw store records; :func:`_shape_for_agent` turns
them into the progressive form the standing instruction promises — files and
resources as *a location plus a summary*, segments naming their source. These pin
that contract: a mirrorable file is bootstrapped to disk and gives way to its
mirror ``path``; an unmappable file (no mirror dir, or no name) keeps its text
inline with no dead ``path``; a segment carries the ``track/name`` id of its
parent file, not a filesystem path; and resources collapse the duplicated
url/local_path down to one ``path``.
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


def test_mirrorable_file_is_bootstrapped_and_replaces_content_with_path(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "BASE_DIR", str(tmp_path))
    # Nothing on disk yet: retrieve now owns this tree and bootstraps the mirror.
    shaped = retrieval._shape_for_agent(_result())

    file = shaped["files"][0]
    assert "content" not in file, "a locatable file hands over a path, not its full text"
    assert "resource_urls" not in file, "the internal link list the instruction never names is dropped"
    # The mirror was written out (space in the name becomes a dash) and its path handed back.
    out_path = tmp_path / "memory" / "coffee-preferences.md"
    assert file["path"] == str(out_path)
    assert out_path.read_text(encoding="utf-8").endswith("No sugar."), "the mirror carries the file's content"


def test_bootstrap_overwrites_a_stale_mirror(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "BASE_DIR", str(tmp_path))
    # A pre-existing mirror with different content must be healed to the store's.
    write_recall_file(tmp_path, "memory", {"name": "coffee preferences", "description": "d", "content": "STALE"})

    shaped = retrieval._shape_for_agent(_result())

    file = shaped["files"][0]
    assert file["path"] == str(tmp_path / "memory" / "coffee-preferences.md")
    assert (tmp_path / "memory" / "coffee-preferences.md").read_text(encoding="utf-8").endswith("No sugar.")


def test_unmappable_file_keeps_content_inline_with_no_path(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "BASE_DIR", str(tmp_path))
    # A file whose track has no mirror directory has nowhere to live: the result
    # must stay self-sufficient and must NOT dangle a path at a file that isn't there.
    result = _result()
    result["files"][0]["track"] = "resource"  # not in TRACK_DIRS

    shaped = retrieval._shape_for_agent(result)

    file = shaped["files"][0]
    assert file["content"] == "No sugar.", "with nowhere to mirror, the text must survive inline"
    assert "path" not in file, "an unmappable file must not leave a dead path for the agent to chase"


def test_segment_names_its_source_file_by_track_and_name(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "BASE_DIR", str(tmp_path))
    shaped = retrieval._shape_for_agent(_result())

    seg = shaped["segments"][0]
    assert "recall_file_id" not in seg, "the internal UUID must not leak to the agent"
    # The label identifies the parent file for lookup — an id, not a path.
    assert seg["source_file"] == "memory/coffee preferences"
    # A segment whose file fell out of the result gets no fabricated label.
    assert shaped["segments"][1]["source_file"] is None


def test_resource_collapses_to_single_path(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "BASE_DIR", str(tmp_path))
    shaped = retrieval._shape_for_agent(_result())

    res = shaped["resources"][0]
    assert res["path"] == "notes/onboarding.md"
    assert "url" not in res and "local_path" not in res
