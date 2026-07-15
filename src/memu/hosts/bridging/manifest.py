"""Snapshot the mirrored recall files by content hash, diff them later.

Prepare records a sha256 of every mirrored file; commit re-hashes and diffs
against that snapshot to learn which files the agent actually created or
modified. Hashing content (not mtime, and not the agent's own account of what it
did) means a rewrite with identical bytes is correctly seen as unchanged.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _iter_tracked(base_dir: Path, subdirs: list[str]) -> Iterator[tuple[str, Path]]:
    """Yield ``(relative-posix key, path)`` for every file under each subdir."""
    for subdir in subdirs:
        root = base_dir / subdir
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file():
                yield path.relative_to(base_dir).as_posix(), path


def snapshot_tracked(base_dir: Path, subdirs: list[str], manifest_path: Path) -> None:
    """Record ``{relative-path: sha256}`` for the tracked files as they stand now."""
    manifest = {key: _hash_file(path) for key, path in _iter_tracked(base_dir, subdirs)}
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def diff_tracked(base_dir: Path, subdirs: list[str], manifest_path: Path) -> list[Path]:
    """Files created or content-changed since the snapshot, in stable order.

    Deletions are intentionally not returned — a file in the manifest but gone
    from disk is dropped silently. Surface those separately if/when the submit
    API grows a removal path.
    """
    baseline = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

    changed: list[Path] = []
    for key, path in _iter_tracked(base_dir, subdirs):
        if baseline.get(key) != _hash_file(path):
            changed.append(path)
    return changed
