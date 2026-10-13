"""Release artifacts: export real package contents and publish only complete revisions."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from memu.hosts import instruction, templates

_spec = importlib.util.spec_from_file_location("sdk_assets", Path(__file__).parents[1] / "scripts" / "sdk_assets.py")
assert _spec and _spec.loader
assets = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(assets)


class Store:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.writes: list[str] = []
        self.fail_on: str | None = None

    def get(self, key: str) -> bytes | None:
        return self.objects.get(key)

    def put(self, key: str, source: Path, content_type: str) -> None:
        if key.endswith(self.fail_on or "NEVER"):
            message = "upload interrupted"
            raise OSError(message)
        self.objects[key] = source.read_bytes()
        self.writes.append(key)


def bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, label: str = "initial") -> tuple[Path, dict[str, Any]]:
    monkeypatch.setattr(assets, "version", lambda _: "0.11.0-beta.3")
    directory = tmp_path / label
    manifest = assets.export(directory, label)
    return directory, manifest


def test_export_preserves_sdk_contract_and_host_url_ids(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory, manifest = bundle(tmp_path, monkeypatch)
    assert manifest["sdk_version"] == "0.11.0b3"
    assert len(manifest["files"]) == 31
    assert "docs/claude-code/INSTALL.md" in manifest["files"]
    assert "docs/agent/INSTALL.md" in manifest["files"]
    assert "docs/pi/UNINSTALL.md" in manifest["files"]
    assert (directory / "instructions/retrieval-skill.txt").read_text() == instruction.skill_document("{binary}")
    assert assets.load_manifest(directory) == manifest
    for name in manifest["files"]:
        text = (directory / name).read_text()
        if name.startswith("instructions/"):
            assert templates._valid(text, templates.REQUIRED_KEYS[Path(name).stem])
        else:
            assert templates._valid_doc(text)


def test_upload_switches_pointer_last_and_requires_explicit_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory, first = bundle(tmp_path, monkeypatch)
    store = Store()
    assets.upload(directory, store)
    pointer = "sdk/0.11.0b3/current.json"
    assert store.writes[-1] == pointer
    assert len(store.writes) == 33  # assets, snapshot manifest, active manifest
    assets.upload(directory, store)  # retry is a no-op
    assert len(store.writes) == 33
    second_directory, second = bundle(tmp_path, monkeypatch, "correction")
    with pytest.raises(ValueError, match="--overwrite"):
        assets.upload(second_directory, store)
    assert json.loads(store.objects[pointer]) == first
    store.fail_on = "INSTALL.md"
    with pytest.raises(OSError, match="interrupted"):
        assets.upload(second_directory, store, overwrite=True)
    assert json.loads(store.objects[pointer]) == first
    store.fail_on = None
    assets.upload(second_directory, store, overwrite=True)
    assert json.loads(store.objects[pointer]) == second
    assert f"sdk/0.11.0b3/revisions/{first['revision']}/manifest.json" in store.objects


def test_modified_bundle_never_uploads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory, _ = bundle(tmp_path, monkeypatch)
    (directory / "instructions/memory-job.txt").write_text("typo {input_path} {track_dir}")
    store = Store()
    with pytest.raises(ValueError, match="checksum"):
        assets.upload(directory, store)
    assert not store.writes


def test_public_verification_checks_manifest_and_body(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory, manifest = bundle(tmp_path, monkeypatch)

    class Response:
        def __init__(self, data: bytes) -> None:
            self.data = data

        def read(self, size: int = -1) -> bytes:
            return self.data if size < 0 else self.data[:size]

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            pass

    def serve(url: str, timeout: int) -> Response:
        path = url.split("/0.11.0b3/", 1)[1]
        return Response((directory / path).read_bytes())

    monkeypatch.setattr(assets.urllib.request, "urlopen", serve)
    assets.verify(directory, "https://example.test/sdk")
    manifest["files"]["instructions/memory-job.txt"]["sha256"] = "0" * 64
    monkeypatch.setattr(assets, "load_manifest", lambda _: manifest)
    with pytest.raises(ValueError, match="manifest differs"):
        assets.verify(directory, "https://example.test/sdk")


@pytest.mark.parametrize("code, missing", [("NoSuchKey", True), ("AccessDenied", False)])
def test_r2_only_treats_missing_objects_as_unpublished(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: str, missing: bool
) -> None:
    import subprocess

    monkeypatch.setattr(assets.shutil, "which", lambda _: "/usr/bin/aws")
    store = assets.R2("bucket", "https://example.test")
    monkeypatch.setattr(
        store, "command", lambda *args: subprocess.CompletedProcess(args, 1, "", f"An error occurred ({code})")
    )
    if missing:
        assert store.get("sdk/0.11.0b3/current.json") is None
    else:
        with pytest.raises(ValueError, match="R2 read failed"):
            store.get("sdk/0.11.0b3/current.json")
