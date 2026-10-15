from __future__ import annotations

import pathlib

from memu.hosts.bridging import resources


def test_verify_resource_log_accepts_windows_absolute_paths(tmp_path: pathlib.Path, monkeypatch) -> None:
    windows_path = r"C:\Users\XnneHang\notes.md"
    log = tmp_path / ".resource.tmp"
    output = tmp_path / "resources.md"
    log.write_text(f"{windows_path}\n", encoding="utf-8")

    monkeypatch.setattr(resources.os.path, "isfile", lambda path: path == windows_path)

    assert resources.verify_resource_log(log, output) == 1
    assert output.read_text(encoding="utf-8") == (f"---\npath: {windows_path}\ndescription: \n---\n")
