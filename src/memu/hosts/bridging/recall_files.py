"""Mirror memU's recall files (memory/skill) to disk as markdown, and back.

The agent does its self-evolve work against plain markdown on disk, not against
the store. Prepare writes the current state out; commit reads back whatever the
agent left behind.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def recall_file_path(base_dir: Path, subdir: str, name: str) -> Path:
    """The on-disk mirror path for a recall file, by name.

    The one place the filename convention lives, so the writer and any reader
    that needs to *locate* a mirrored file by name (e.g. retrieval, surfacing a
    file's path to the agent) agree by construction rather than by comment.
    """
    # Escape spaces in the filename with '-'; the frontmatter keeps the raw name.
    return base_dir / subdir / f"{name.replace(' ', '-')}.md"


def write_recall_file(base_dir: Path, subdir: str, recall_file: dict[str, Any]) -> Path:
    """Mirror one recall file into ``base_dir/subdir`` as front-mattered markdown."""
    name = recall_file["name"]
    description = recall_file.get("description", "")
    content = recall_file.get("content") or ""

    out_dir = base_dir / subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = recall_file_path(base_dir, subdir, name)
    out_path.write_text(f"---\nname: {name}\ndescription: {description}\n---\n{content}", encoding="utf-8")
    return out_path


def read_recall_file(path: Path, track: str) -> dict[str, Any]:
    """Inverse of :func:`write_recall_file` — parse a mirrored file back into a dict.

    Recovers name/description from the frontmatter and content from the body,
    tagging it with the ``track`` its directory represents (the file itself does
    not store the track). Mirrors the fields ``list_all_recall_files`` returns.
    """
    text = path.read_text(encoding="utf-8")
    name = ""
    description = ""
    content = text
    if text.startswith("---\n"):
        # maxsplit=2 keeps any '---' lines inside the content intact.
        _, frontmatter, content = text.split("---\n", 2)
        for line in frontmatter.splitlines():
            key, sep, value = line.partition(":")
            if not sep:
                continue
            if key.strip() == "name":
                name = value.strip()
            elif key.strip() == "description":
                description = value.strip()
    return {"name": name, "track": track, "description": description, "content": content}
