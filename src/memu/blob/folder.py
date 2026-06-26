"""Folder scanning, modality inference, and input-side manifest diffing.

The folder-based ``memorize`` entry point treats a directory as the unit of
ingestion. This module is responsible for the *input* side of the sync:

- recursively scan a folder for ingestible files,
- infer each file's modality from its extension (skipping unknown types),
- maintain a sidecar ``.memu_manifest.json`` (``relative path -> content hash``)
  so each call can tell which files were added, modified, or deleted.

This is independent of the *output* side manifest used by ``memu.memory_fs``
(which hashes the rendered markdown artifacts).
"""

from __future__ import annotations

import hashlib
import json
import logging
import pathlib
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

MANIFEST_FILENAME = ".memu_manifest.json"

# Extension -> modality. Ambiguous extensions (.json, .webm) are mapped to a
# single sensible default and can be made configurable later if needed.
EXT_MODALITY: dict[str, str] = {
    ".json": "conversation",
    ".txt": "document",
    ".md": "document",
    ".text": "document",
    # Rich document formats converted to Markdown via MarkItDown on ingest.
    ".pdf": "document",
    ".docx": "document",
    ".doc": "document",
    ".pptx": "document",
    ".ppt": "document",
    ".xlsx": "document",
    ".xls": "document",
    ".html": "document",
    ".htm": "document",
    ".epub": "document",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".gif": "image",
    ".webp": "image",
    ".mp4": "video",
    ".mov": "video",
    ".mkv": "video",
    ".avi": "video",
    ".mp3": "audio",
    ".wav": "audio",
    ".m4a": "audio",
    ".mpeg": "audio",
    ".mpga": "audio",
}


@dataclass(frozen=True)
class ScannedFile:
    """A single ingestible file discovered in the scanned folder."""

    rel_path: str
    abs_path: str
    modality: str
    content_hash: str


@dataclass
class FolderDiff:
    """The added/modified/deleted sets between a scan and the prior manifest."""

    added: list[ScannedFile] = field(default_factory=list)
    modified: list[ScannedFile] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.modified or self.deleted)

    @property
    def has_removals(self) -> bool:
        """Whether any file was modified or deleted (i.e. stale memory exists)."""
        return bool(self.modified or self.deleted)


def infer_modality(path: str | pathlib.Path) -> str | None:
    """Infer modality from a file extension, or None if unsupported."""
    return EXT_MODALITY.get(pathlib.Path(path).suffix.lower())


def compute_file_hash(path: str | pathlib.Path) -> str:
    """Content hash (sha256) of a file, streamed to stay memory-friendly."""
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_folder(folder: str | pathlib.Path) -> dict[str, ScannedFile]:
    """Recursively scan a folder for ingestible files keyed by relative path.

    Hidden files/dirs (dot-prefixed), the manifest itself, and files with an
    unknown extension are skipped (the latter is logged).
    """
    root = pathlib.Path(folder).resolve()
    scanned: dict[str, ScannedFile] = {}
    if not root.is_dir():
        msg = f"memorize() expects an existing folder, got: {folder}"
        raise NotADirectoryError(msg)

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == MANIFEST_FILENAME:
            continue
        rel = path.relative_to(root)
        if any(part.startswith(".") for part in rel.parts):
            continue
        modality = infer_modality(path)
        if modality is None:
            logger.warning("Skipping file with unsupported extension: %s", rel)
            continue
        rel_str = rel.as_posix()
        scanned[rel_str] = ScannedFile(
            rel_path=rel_str,
            abs_path=str(path),
            modality=modality,
            content_hash=compute_file_hash(path),
        )
    return scanned


def load_manifest(folder: str | pathlib.Path) -> dict[str, str]:
    """Load the sidecar input manifest (``relative path -> content hash``)."""
    manifest_path = pathlib.Path(folder).resolve() / MANIFEST_FILENAME
    if not manifest_path.exists():
        return {}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items()}


def save_manifest(folder: str | pathlib.Path, manifest: dict[str, str]) -> None:
    """Persist the input manifest into the scanned folder."""
    manifest_path = pathlib.Path(folder).resolve() / MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def diff_folder(scanned: dict[str, ScannedFile], manifest: dict[str, str]) -> FolderDiff:
    """Compute added/modified/deleted relative to a prior manifest."""
    diff = FolderDiff()
    for rel, scanned_file in scanned.items():
        prior_hash = manifest.get(rel)
        if prior_hash is None:
            diff.added.append(scanned_file)
        elif prior_hash != scanned_file.content_hash:
            diff.modified.append(scanned_file)
    diff.deleted = [rel for rel in manifest if rel not in scanned]
    return diff


def manifest_from_scan(scanned: dict[str, ScannedFile]) -> dict[str, str]:
    """Build the manifest payload to persist from a fresh scan."""
    return {rel: scanned_file.content_hash for rel, scanned_file in scanned.items()}


__all__ = [
    "EXT_MODALITY",
    "MANIFEST_FILENAME",
    "FolderDiff",
    "ScannedFile",
    "compute_file_hash",
    "diff_folder",
    "infer_modality",
    "load_manifest",
    "manifest_from_scan",
    "save_manifest",
]
