from __future__ import annotations

from pathlib import Path

import pytest

from memu.hosts.bridging import resources


def test_verify_retains_existing_native_absolute_paths(tmp_path: Path) -> None:
    artifact = tmp_path / "agent notes.md"
    artifact.write_text("Agent task output", encoding="utf-8")
    log = tmp_path / ".resource.tmp"
    output = tmp_path / "resources.md"
    log.write_text(f"{artifact}\n{artifact}\n{tmp_path / 'missing.md'}\n", encoding="utf-8")

    assert resources.verify_resource_log(log, output) == 1
    assert output.read_text(encoding="utf-8") == f"---\npath: {artifact}\ndescription: \n---\n"


@pytest.mark.parametrize("path", [r"C:\workspace\notes.md", "C:/workspace/notes.md", r"\\server\share\notes.md"])
def test_verify_accepts_windows_absolute_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, path: str) -> None:
    log = tmp_path / ".resource.tmp"
    output = tmp_path / "resources.md"
    log.write_text(f"{path}\n", encoding="utf-8")
    monkeypatch.setattr(resources.os.path, "isfile", lambda candidate: candidate == path)

    assert resources.verify_resource_log(log, output) == 1
    assert f"path: {path}\n" in output.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", ["notes.md", "./notes.md", "../notes.md", "C:notes.md", r"\notes.md"])
def test_verify_rejects_relative_paths_even_when_they_exist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    log = tmp_path / ".resource.tmp"
    output = tmp_path / "resources.md"
    log.write_text(f"{path}\n", encoding="utf-8")
    monkeypatch.setattr(resources.os.path, "isfile", lambda _candidate: True)

    assert resources.verify_resource_log(log, output) == 0
    assert output.read_text(encoding="utf-8") == "---\n"


@pytest.mark.parametrize("path", ["/workspace/notes.md", "~/notes.md"])
def test_verify_preserves_posix_and_home_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, path: str) -> None:
    log = tmp_path / ".resource.tmp"
    output = tmp_path / "resources.md"
    log.write_text(f"{path}\n", encoding="utf-8")
    monkeypatch.setattr(resources.os.path, "isfile", lambda _candidate: True)

    assert resources.verify_resource_log(log, output) == 1
    assert f"path: {path}\n" in output.read_text(encoding="utf-8")


def test_verify_keeps_first_seen_order_and_resource_limit(tmp_path: Path) -> None:
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("First", encoding="utf-8")
    second.write_text("Second", encoding="utf-8")
    log = tmp_path / ".resource.tmp"
    output = tmp_path / "resources.md"
    log.write_text(f"{first}\n{first}\n{second}\n", encoding="utf-8")

    assert resources.verify_resource_log(log, output, max_resources=1) == 1
    assert f"path: {first}\n" in output.read_text(encoding="utf-8")
    assert str(second) not in output.read_text(encoding="utf-8")
