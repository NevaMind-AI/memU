"""Host retrieval hits carry matched text and its source details together."""

from __future__ import annotations

import copy
import pathlib
from types import SimpleNamespace

import pytest

from memu import env
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


def test_projection_limits_hits_to_first_five_without_limiting_resources(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "BASE_DIR", str(tmp_path))
    result = _result()
    result["segments"] = [
        {"recall_file_id": "f1", "text": f"excerpt {index}", "score": 1 - index / 10} for index in range(8)
    ]
    result["resources"] = [{"url": f"notes/{index}.md", "caption": "notes"} for index in range(6)]

    shaped = retrieval._shape_for_agent(result)

    assert [hit["text"] for hit in shaped["hits"]] == [f"excerpt {index}" for index in range(5)]
    assert [hit["score"] for hit in shaped["hits"]] == [1 - index / 10 for index in range(5)]
    assert len(shaped["resources"]) == 6


def test_projection_returns_empty_layers() -> None:
    assert retrieval._shape_for_agent({}) == {"hits": [], "resources": []}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("query", "kind", "expected"),
    [
        ("topic", None, 1),
        ("中" * 199 + " \n", None, 1),
        ("中" * 200, None, 0),
        ("topic", "long", 0),
        ("topic", "extracted", 1),
    ],
)
@pytest.mark.parametrize("mode", ["local", "cloud"])
async def test_configured_cutoff_filters_before_mirroring(tmp_path, monkeypatch, query, kind, expected, mode):
    monkeypatch.setattr(env, "_file_values", lambda: {})
    monkeypatch.setenv("MEMU_MEMORY_MODE", mode)
    for category, score in (("SHORT", "0.4"), ("LONG", "0.6"), ("EXTRACTED", "0.4")):
        monkeypatch.setenv(f"MEMU_{mode.upper()}_RETRIEVE_MIN_SCORE_{category}", score)
    seen = []

    async def search(query, where):
        seen.append(where)
        return _result()

    monkeypatch.setattr(
        retrieval, "build_agentic_memory_backend_from_env", lambda: SimpleNamespace(progressive_retrieve=search)
    )
    monkeypatch.setattr(retrieval, "BASE_DIR", str(tmp_path))
    result = await retrieval.retrieve(query, where={"user_id": "u"}, query_kind=kind)
    assert seen == [{"user_id": "u"}]
    assert len(result["hits"]) == expected
    assert result["retrieval_status"] == {
        "status": "succeeded",
        "query_kind": kind or ("long" if query == "中" * 200 else "short"),
        "min_score": 0.6 if expected == 0 else 0.4,
        "candidate_segments": 2,
        "filtered_segments": 2 - expected,
        "retained_segments": expected,
        "returned_hits": expected,
    }
    assert (tmp_path / "memory/coffee-preferences.md").exists() is bool(expected)
    assert len(result["resources"]) == 1  # Segment calibration does not cover resources.


@pytest.mark.asyncio
async def test_disabled_filter_reports_successful_unfiltered_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(env, "_file_values", lambda: {})
    monkeypatch.setenv("MEMU_MEMORY_MODE", "local")
    monkeypatch.delenv("MEMU_LOCAL_RETRIEVE_MIN_SCORE_SHORT", raising=False)

    async def search(query, where):
        return _result()

    monkeypatch.setattr(
        retrieval, "build_agentic_memory_backend_from_env", lambda: SimpleNamespace(progressive_retrieve=search)
    )
    monkeypatch.setattr(retrieval, "BASE_DIR", str(tmp_path))
    result = await retrieval.retrieve("topic")
    assert result["retrieval_status"] == {
        "status": "succeeded",
        "query_kind": "short",
        "min_score": None,
        "candidate_segments": 2,
        "filtered_segments": 0,
        "retained_segments": 2,
        "returned_hits": 2,
    }


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "1.01", "-1.01", "invalid"])
@pytest.mark.parametrize("mode", ["local", "cloud"])
def test_invalid_cutoff_is_rejected(monkeypatch, value, mode):
    monkeypatch.setenv("MEMU_MEMORY_MODE", mode)
    name = f"MEMU_{mode.upper()}_RETRIEVE_MIN_SCORE_SHORT"
    monkeypatch.setenv(name, value)
    with pytest.raises(env.ConfigError, match=name):
        env.retrieval_min_score("short")


@pytest.mark.parametrize("mode", ["local", "cloud"])
def test_cutoff_uses_shared_config_and_environment_override(monkeypatch, mode):
    monkeypatch.setenv("MEMU_MEMORY_MODE", mode)
    name = f"MEMU_{mode.upper()}_RETRIEVE_MIN_SCORE_SHORT"
    monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(env, "_file_values", lambda: {})
    assert env.retrieval_min_score("short") == (0.55 if mode == "cloud" else None)
    monkeypatch.setattr(env, "_file_values", lambda: {name: "0.65"})
    assert env.retrieval_min_score("short") == 0.65
    monkeypatch.setenv(name, "0")
    assert env.retrieval_min_score("short") == 0


@pytest.mark.parametrize("mode", ["local", "cloud"])
@pytest.mark.parametrize(("kind", "cloud_default"), [("short", 0.55), ("long", 0.60), ("extracted", 0.58)])
def test_backend_cutoffs_are_independent(monkeypatch, mode, kind, cloud_default):
    monkeypatch.setenv("MEMU_MEMORY_MODE", mode)
    monkeypatch.setattr(env, "_file_values", lambda: {})
    monkeypatch.delenv(f"MEMU_{mode.upper()}_RETRIEVE_MIN_SCORE_{kind.upper()}", raising=False)
    other_mode = "LOCAL" if mode == "cloud" else "CLOUD"
    monkeypatch.setenv(f"MEMU_{other_mode}_RETRIEVE_MIN_SCORE_{kind.upper()}", "invalid")
    assert env.retrieval_min_score(kind) == (cloud_default if mode == "cloud" else None)
    # Switching backends selects that backend's independently configured threshold.
    monkeypatch.setenv(f"MEMU_{other_mode}_RETRIEVE_MIN_SCORE_{kind.upper()}", "0.75")
    monkeypatch.setenv("MEMU_MEMORY_MODE", other_mode.lower())
    assert env.retrieval_min_score(kind) == 0.75
