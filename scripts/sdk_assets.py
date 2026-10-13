"""Export the installed memu-cli wheel, publish to R2, and verify public assets.

Run export in an isolated environment containing the exact release wheel. No
website checkout is needed. Upload uses the AWS CLI and its normal credentials.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import urllib.request
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path
from typing import Any

VERSION_RE = re.compile(r"[0-9][a-zA-Z0-9.!+_-]*\Z")
ASSET_RE = re.compile(r"(?:instructions/[a-z-]+\.txt|docs/[a-z-]+/(?:INSTALL|BRIDGING_TASK|UNINSTALL)\.md)\Z")


def fail(message: str) -> None:
    raise ValueError(message)


def encoded(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def collect() -> dict[str, str]:
    """Export raw placeholders, including URL host ids declared by each adapter."""
    from memu.hosts import instruction, templates
    from memu.hosts.bridging.instructions import MEMORY_JOB_TEMPLATE, SKILL_JOB_TEMPLATE
    from memu.hosts.bridging.resources import RESOURCE_JOB_TEMPLATE

    assets = {
        "instructions/memory-job.txt": MEMORY_JOB_TEMPLATE,
        "instructions/skill-job.txt": SKILL_JOB_TEMPLATE,
        "instructions/resource-job.txt": RESOURCE_JOB_TEMPLATE,
        "instructions/retrieval-skill.txt": instruction.skill_document("{binary}"),
    }
    for package in sorted(files("memu.hosts").iterdir(), key=lambda item: item.name):
        if not package.joinpath("INSTALL.md").is_file():
            continue
        tree = ast.parse(package.joinpath("cli.py").read_text(encoding="utf-8"))
        host = next(
            ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "HOST" for target in node.targets)
        )
        for filename in ("INSTALL.md", "BRIDGING_TASK.md", "UNINSTALL.md"):
            assets[f"docs/{host}/{filename}"] = package.joinpath(filename).read_text(encoding="utf-8")
    for path, text in assets.items():
        valid = (
            templates._valid(text, templates.REQUIRED_KEYS[Path(path).stem])
            if path.startswith("instructions/")
            else templates._valid_doc(text)
        )
        if not valid or not ASSET_RE.fullmatch(path) or len(text.encode()) > 64 * 1024:
            fail(f"Invalid SDK asset: {path}")
    return assets


def export(output: Path, source_commit: str) -> dict[str, Any]:
    from packaging.version import Version

    sdk_version = str(Version(version("memu-cli")))  # wheel METADATA, never the workflow input/tag
    if not VERSION_RE.fullmatch(sdk_version) or sdk_version == "0+unknown":
        fail(f"Invalid installed distribution version: {sdk_version}")
    assets = collect()
    manifest: dict[str, Any] = {
        "schema": 1,
        "sdk_version": sdk_version,
        "source_commit": source_commit,
        "files": {
            name: {"sha256": digest(text.encode()), "size": len(text.encode())} for name, text in sorted(assets.items())
        },
    }
    manifest["revision"] = digest(encoded(manifest))
    # A fresh directory prevents unrelated/stale files entering a publication.
    output.mkdir(parents=True, exist_ok=False)
    for name, text in assets.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode())
    (output / "manifest.json").write_bytes(encoded(manifest))
    return manifest


def load_manifest(directory: Path) -> dict[str, Any]:
    manifest: dict[str, Any] = json.loads((directory / "manifest.json").read_bytes())
    base = {key: value for key, value in manifest.items() if key != "revision"}
    if (
        manifest.get("schema") != 1
        or not VERSION_RE.fullmatch(manifest.get("sdk_version", ""))
        or manifest.get("revision") != digest(encoded(base))
        or not manifest.get("source_commit")
        or not manifest.get("files")
    ):
        fail("Invalid SDK manifest")
    for name, info in manifest["files"].items():
        if not ASSET_RE.fullmatch(name):
            fail(f"Invalid asset path: {name}")
        data = (directory / name).read_bytes()
        if info != {"sha256": digest(data), "size": len(data)} or len(data) > 64 * 1024:
            fail(f"Asset checksum/size mismatch: {name}")
    return manifest


class R2:
    """Thin AWS CLI transport; authorization failures must never look like 404s."""

    def __init__(self, bucket: str, endpoint: str) -> None:
        self.executable = shutil.which("aws")
        if self.executable is None:
            fail("AWS CLI is required for upload")
        self.bucket = bucket
        self.endpoint = endpoint

    def command(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603 — fixed executable, argv only
            [self.executable, "--endpoint-url", self.endpoint, "--region", "auto", "s3api", *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def get(self, key: str) -> bytes | None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "object"
            result = self.command("get-object", "--bucket", self.bucket, "--key", key, str(target))
            if result.returncode:
                if "(NoSuchKey)" in result.stderr:
                    return None
                fail(f"R2 read failed: {result.stderr.strip()}")
            return target.read_bytes()

    def put(self, key: str, source: Path, content_type: str) -> None:
        result = self.command(
            "put-object", "--bucket", self.bucket, "--key", key, "--body", str(source), "--content-type", content_type
        )
        if result.returncode:
            fail(f"R2 upload failed: {result.stderr.strip()}")


def upload(directory: Path, store: R2, *, overwrite: bool = False) -> dict[str, Any]:
    manifest = load_manifest(directory)
    root = f"sdk/{manifest['sdk_version']}"
    current = store.get(f"{root}/current.json")
    if current is not None:
        if json.loads(current) == manifest:
            return manifest  # idempotent retry
        if not overwrite:
            fail("Version already published with different content; use --overwrite for a reviewed correction")
    revision_root = f"{root}/revisions/{manifest['revision']}"
    # Immutable snapshots retain the previous publication for recovery. Only
    # current.json changes; incomplete uploads are invisible to the Worker.
    for name in manifest["files"]:
        content_type = "text/markdown; charset=utf-8" if name.endswith(".md") else "text/plain; charset=utf-8"
        store.put(f"{revision_root}/{name}", directory / name, content_type)
    store.put(f"{revision_root}/manifest.json", directory / "manifest.json", "application/json")
    store.put(f"{root}/current.json", directory / "manifest.json", "application/json")
    return manifest


def verify(directory: Path, base_url: str) -> None:
    manifest = load_manifest(directory)
    root = f"{base_url.rstrip('/')}/{manifest['sdk_version']}"
    with urllib.request.urlopen(f"{root}/manifest.json", timeout=20) as response:  # noqa: S310 — operator URL
        if json.loads(response.read()) != manifest:
            fail("Public manifest differs from the uploaded revision")
    for name, info in manifest["files"].items():
        with urllib.request.urlopen(f"{root}/{name}", timeout=20) as response:  # noqa: S310
            data = response.read(64 * 1024 + 1)
        if digest(data) != info["sha256"] or len(data) != info["size"]:
            fail(f"Public asset differs from publication: {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export_parser = commands.add_parser("export")
    export_parser.add_argument("--output", type=Path, required=True)
    export_parser.add_argument("--source-commit", required=True)
    upload_parser = commands.add_parser("upload")
    upload_parser.add_argument("--directory", type=Path, required=True)
    upload_parser.add_argument("--bucket", required=True)
    upload_parser.add_argument("--endpoint", required=True)
    upload_parser.add_argument("--overwrite", action="store_true")
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("--directory", type=Path, required=True)
    verify_parser.add_argument("--base-url", default="https://memu.pro/sdk")
    args = parser.parse_args()
    if args.command == "export":
        manifest = export(args.output, args.source_commit)
    elif args.command == "upload":
        manifest = upload(args.directory, R2(args.bucket, args.endpoint), overwrite=args.overwrite)
    else:
        verify(args.directory, args.base_url)
        return
    print(f"{manifest['sdk_version']}: {len(manifest['files'])} files, revision {manifest['revision']}")


if __name__ == "__main__":
    main()
