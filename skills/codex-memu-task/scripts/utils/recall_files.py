"""Step 2 — mirror recall files (memory/skill) to disk as markdown."""

from pathlib import Path


def write_recall_file(base_dir: Path, subdir: str, recall_file: dict) -> Path:
    name = recall_file["name"]
    description = recall_file.get("description", "")
    content = recall_file.get("content") or ""

    out_dir = base_dir / subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Escape spaces in the filename with '-'; the frontmatter keeps the raw name.
    filename = f"{name.replace(' ', '-')}.md"
    out_path = out_dir / filename

    body = f"---\nname: {name}\ndescription: {description}\n---\n{content}"
    out_path.write_text(body, encoding="utf-8")
    return out_path


def read_recall_file(path: Path, track: str) -> dict:
    """Inverse of write_recall_file — parse a mirrored file back into a dict.

    Recovers name/description from the frontmatter and content from the body,
    tagging it with the `track` its directory represents (the file itself does
    not store the track). Mirrors the fields list_all_recall_files returns:
    name + track + description + content.
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
