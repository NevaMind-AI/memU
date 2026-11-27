"""Mirror memU's recall files (memory/skill) to disk as markdown, and back.

The agent does its self-evolve work against plain markdown on disk, not against
the store. Prepare writes the current state out; commit reads back whatever the
agent left behind.
"""

from __future__ import annotations

import contextlib
import os
import re
import tempfile
from pathlib import Path
from typing import Any


def _atomic_write_text(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` so a concurrent reader never sees it half-written.

    The inject hook (``retrieval``) now writes mirror files on the per-turn hot
    path while agents read them, so a plain ``write_text`` could hand back a torn
    file. Write to a uniquely-named temp in the same directory (so the final
    ``os.replace`` is a same-filesystem atomic rename) and swap it in whole. The
    unique temp name also lets two writers of the same target run without
    clobbering each other's in-progress file — last rename wins, and since both
    derive their content from the same store, the content is identical anyway.
    """
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        # Never leave the temp file behind if the write or rename failed.
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def recall_file_path(base_dir: Path, subdir: str, name: str) -> Path:
    """The on-disk mirror path for a recall file, by name.

    The one place the filename convention lives, so the writer and any reader
    that needs to *locate* a mirrored file by name (e.g. retrieval, surfacing a
    file's path to the agent) agree by construction rather than by comment.
    """
    # Keep legacy spaced names at their existing mirror paths; frontmatter retains
    # the stored name. Names normalized by commit contain no spaces, so this is a
    # no-op for them. Existing legacy collisions require separate reconciliation.
    return base_dir / subdir / f"{name.replace(' ', '-')}.md"


def write_recall_file(base_dir: Path, subdir: str, recall_file: dict[str, Any]) -> Path | None:
    """Mirror a recall file, or remove its mirror when a memory body is empty."""
    name = recall_file["name"]
    description = recall_file.get("description", "")
    content = recall_file.get("content") or ""

    out_path = recall_file_path(base_dir, subdir, name)
    if subdir == "memory" and not content.strip():
        out_path.unlink(missing_ok=True)
        return None

    out_dir = base_dir / subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    _atomic_write_text(out_path, f"---\nname: {name}\ndescription: {description}\n---\n{content}")
    return out_path


def read_recall_file(path: Path, track: str) -> dict[str, Any]:
    """Inverse of :func:`write_recall_file` — parse a mirrored file back into a dict.

    Recovers name/description from the frontmatter and content from the body,
    tagging it with the ``track`` its directory represents (the file itself does
    not store the track). Mirrors the fields ``list_all_recall_files`` returns.
    Frontmatter delimiters occupy standalone ``---`` lines; a name or description
    ending in ``---`` remains metadata. Empty memory bodies require an explicit
    ``empty: true`` acknowledgement; non-empty bodies take precedence over it.
    The acknowledgement is local metadata and is not sent to the backend.
    """
    text = path.read_text(encoding="utf-8")
    empty_markers: list[str] = []
    name = ""
    description = ""
    content = text
    if text.startswith("---\n"):
        # Delimiters occupy a whole line; metadata may itself end in '---'.
        # maxsplit=2 keeps any delimiter lines inside the body intact.
        _, frontmatter, content = re.split(r"^---\n", text, maxsplit=2, flags=re.MULTILINE)
        for line in frontmatter.splitlines():
            key, sep, value = line.partition(":")
            if not sep:
                continue
            if key.strip() == "name":
                name = value.strip()
            elif key.strip() == "description":
                description = value.strip()
            elif key.strip() == "empty":
                empty_markers.append(value.strip())
    if not name:
        msg = f"recall file {path.name!r} requires a non-empty name in frontmatter"
        raise ValueError(msg)
    if track == "memory" and not content.strip() and empty_markers != ["true"]:
        msg = f"recall file {path.name!r} requires empty: true in frontmatter to submit an empty memory body"
        raise ValueError(msg)
    return {"name": name, "track": track, "description": description, "content": content}


def finalize_recall_file(path: Path, recall_file: dict[str, Any]) -> None:
    """After successful commit, remove cleared mirrors or consume stale empty markers."""
    if recall_file["track"] != "memory":
        return
    if not recall_file["content"].strip():
        path.unlink(missing_ok=True)
        return
    text = path.read_text(encoding="utf-8")
    _, frontmatter, content = re.split(r"^---\n", text, maxsplit=2, flags=re.MULTILINE)
    cleaned = re.sub(r"^[ \t]*empty[ \t]*:[^\n]*\n?", "", frontmatter, flags=re.MULTILINE)
    if cleaned != frontmatter:
        _atomic_write_text(path, f"---\n{cleaned}---\n{content}")
