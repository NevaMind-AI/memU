"""Recall-file names must keep their identity when mirrored to disk."""

from pathlib import Path

import pytest

from memu.hosts.bridging.recall_files import read_recall_file, write_recall_file


@pytest.mark.parametrize("track", ["memory", "skill"])
@pytest.mark.parametrize("reverse", [False, True])
def test_distinct_names_survive_mirroring(tmp_path: Path, track: str, reverse: bool) -> None:
    names = ["project preferences", "project-preferences", "project%20preferences", "project%2520preferences"]
    if reverse:
        names.reverse()
    paths = {
        name: write_recall_file(tmp_path, track, {"name": name, "content": f"Content for {name}"}) for name in names
    }

    assert len(set(paths.values())) == len(names)
    for name, path in paths.items():
        assert read_recall_file(path, track) == {
            "name": name,
            "track": track,
            "description": "",
            "content": f"Content for {name}",
        }
        assert write_recall_file(tmp_path, track, {"name": name, "content": "Updated"}) == path
        assert read_recall_file(path, track)["content"] == "Updated"
    assert paths["project-preferences"] == tmp_path / track / "project-preferences.md"


def test_legacy_mirror_is_not_deleted_or_used_for_a_spaced_name(tmp_path: Path) -> None:
    directory = tmp_path / "memory"
    directory.mkdir()
    legacy = directory / "project-preferences.md"
    pending = "---\nname: project preferences\ndescription: draft\n---\nUncommitted edit"
    legacy.write_text(pending, encoding="utf-8")

    current = write_recall_file(tmp_path, "memory", {"name": "project preferences", "content": "Stored"})

    assert current != legacy
    assert legacy.read_text(encoding="utf-8") == pending
    assert read_recall_file(current, "memory")["content"] == "Stored"
