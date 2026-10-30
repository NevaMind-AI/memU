"""Seed the packaged install/uninstall skill into the user's store at setup time.

A user who wants memU gone says "uninstall memU" — not "read SKILL.md and follow
its uninstall section". An agent whose context holds no route to the packaged
guide improvises, and an improvised teardown deletes too much (the store) or too
little (the bridging task). Retrieval is a channel that can carry that route: if
the root ``SKILL.md`` sits in the store as a ``skill``-track recall file, a bare
"uninstall memU" can surface it on *any* host sharing the store — including hosts
whose instruction file was never patched, or was hand-edited since.

So setup plants it once. The seed is the packaged ``SKILL.md`` verbatim: its
frontmatter is already the recall-file convention (``name``/``description``), its
description already names the triggers ("install, set up, integrate, remove, or
uninstall memU"), and that description is exactly what gets embedded — the
retrieval surface. Committing through ``commit_results`` makes reseeding an
upsert: a later install refreshes the stored copy instead of stacking a twin.

The mirror under ``~/.memu/skill/`` is written too, for the same reason bridging
mirrors everything: the agent's working medium is markdown on disk, and a seeded
file the self-evolve loop cannot see is a file it would recreate or contradict.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any

from memu.hosts.bridging.layout import TRACK_DIRS
from memu.hosts.bridging.recall_files import parse_recall_text, write_recall_file

SEED_TRACK = "skill"


def seed_document() -> str:
    """The packaged root ``SKILL.md``, falling back to the repo checkout.

    The wheel force-includes the repo-root ``SKILL.md`` as ``memu/SKILL.md`` (see
    ``pyproject.toml``); an editable/dev checkout has no such copy, so fall back
    to the file three levels up from this module. One source document either way
    — never a second copy that can drift.
    """
    packaged = files("memu") / "SKILL.md"
    if packaged.is_file():
        return packaged.read_text(encoding="utf-8")
    return (Path(__file__).resolve().parents[3] / "SKILL.md").read_text(encoding="utf-8")


def seed_recall_file() -> dict[str, Any]:
    """``SKILL.md`` parsed into the shape ``commit_results`` expects.

    The document's own frontmatter supplies ``name`` and ``description`` — the
    description is what gets embedded, and it already carries the uninstall
    trigger words. No rewriting here: the skill's author owns the retrieval
    surface, not the seeder.
    """
    return parse_recall_text(seed_document(), track=SEED_TRACK)


async def seed(base_dir: Path) -> tuple[Path, dict[str, Any]]:
    """Plant the skill: mirror it under ``base_dir`` and upsert it into the store.

    Returns ``(mirror_path, commit result)``. Deliberately store-first in spirit
    but mirror-first in order: the mirror write is local and cannot half-fail,
    while the commit needs the backend — if that raises, the caller reruns this
    whole command and the mirror write is an idempotent overwrite.
    """
    from memu.env import build_agentic_memory_backend_from_env

    recall_file = seed_recall_file()
    mirror = write_recall_file(base_dir, TRACK_DIRS[SEED_TRACK], recall_file)
    backend = build_agentic_memory_backend_from_env()
    result: dict[str, Any] = await backend.commit_results(recall_files=[recall_file])
    return mirror, result
