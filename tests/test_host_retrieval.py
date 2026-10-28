"""Host retrieval hits carry matched text and its source details together."""

from __future__ import annotations

import copy
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


def test_hit_joins_text_to_bootstrapped_source_path(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "BASE_DIR", str(tmp_path))
    shaped = retrieval._shape_for_agent(_result())
    out_path = tmp_path / "memory" / "coffee-preferences.md"
    assert shaped == {
        "hits": [
            {
                "text": "No sugar.",
                "track": "memory",
                "score": 0.4,
                "description": "How the user likes their coffee",
                "path": str(out_path),
            },
            {"text": "orphan", "track": "memory", "score": 0.3},
        ],
        "resources": [{"path": "notes/onboarding.md", "caption": "notes"}],
    }
    assert out_path.read_text(encoding="utf-8").endswith("No sugar.")


def test_bootstrap_overwrites_a_stale_mirror(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "BASE_DIR", str(tmp_path))
    write_recall_file(tmp_path, "memory", {"name": "coffee preferences", "description": "d", "content": "STALE"})
    shaped = retrieval._shape_for_agent(_result())
    assert shaped["hits"][0]["path"] == str(tmp_path / "memory" / "coffee-preferences.md")
    assert (tmp_path / "memory" / "coffee-preferences.md").read_text(encoding="utf-8").endswith("No sugar.")


def test_unmappable_source_keeps_content_inline_with_no_path(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "BASE_DIR", str(tmp_path))
    result = _result()
    result["files"][0]["track"] = "resource"
    hit = retrieval._shape_for_agent(result)["hits"][0]
    assert hit["content"] == "No sugar."
    assert "path" not in hit


def test_multiple_segments_share_source_but_keep_order_and_scores(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "BASE_DIR", str(tmp_path))
    result = _result()
    result["segments"].append({"recall_file_id": "f1", "text": "Black coffee.", "score": 0.2})
    hits = retrieval._shape_for_agent(result)["hits"]
    assert [hit["text"] for hit in hits] == ["No sugar.", "orphan", "Black coffee."]
    assert [hit["score"] for hit in hits] == [0.4, 0.3, 0.2]
    assert hits[0]["path"] == hits[2]["path"]
    assert hits[0]["description"] == hits[2]["description"]


def test_source_only_hit_is_preserved(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "BASE_DIR", str(tmp_path))
    result = _result()
    result["segments"] = []
    hits = retrieval._shape_for_agent(result)["hits"]
    assert len(hits) == 1
    assert hits[0]["description"] == "How the user likes their coffee"
    assert hits[0]["score"] == 0.4
    assert "text" not in hits[0]
    assert hits[0]["path"] == str(tmp_path / "memory" / "coffee-preferences.md")


def test_projection_retains_source_timestamps_and_removes_metadata(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "BASE_DIR", str(tmp_path))
    result = _result()
    metadata = {"user_id": "u1", "agent_id": "a1", "user_name": None, "agent_name": None, "custom_scope": "private"}
    for records in result.values():
        for record in records:
            record.update(metadata, created_at="segment-created", updated_at="segment-updated")
    result["files"][0].update(created_at="source-created", updated_at="source-updated", score=0.9)
    original = copy.deepcopy(result)
    shaped = retrieval._shape_for_agent(result)
    hit = shaped["hits"][0]
    assert hit["created_at"] == "source-created"
    assert hit["updated_at"] == "source-updated"
    assert hit["score"] == 0.4
    assert "created_at" not in shaped["hits"][1], "missing sources must not fabricate source timestamps"
    assert shaped["resources"][0]["created_at"] == "segment-created"
    for records in shaped.values():
        for record in records:
            assert (
                not (set(metadata) | {"id", "name", "recall_file_id", "source_file", "resource_urls"}) & record.keys()
            )
    assert result == original


def test_projection_returns_empty_layers() -> None:
    assert retrieval._shape_for_agent({}) == {"hits": [], "resources": []}
