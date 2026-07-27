"""The seed skill: does setup plant the uninstall route where retrieval can find it?

A bare "uninstall memU" carries no pointer to the packaged guide; the seeded
``SKILL.md`` in the skill track is what retrieval surfaces instead. These pin the
seam's three properties: the seed is the packaged document verbatim (its own
frontmatter is the retrieval surface), planting writes both the mirror and the
store, and replanting is an upsert rather than a twin.
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest

from memu.hosts import seed
from memu.hosts.bridging.recall_files import read_recall_file
from memu.hosts.codex.cli import build_parser


def test_seed_is_the_packaged_skill_with_its_own_frontmatter() -> None:
    """The document's author owns the retrieval surface — the seeder rewrites nothing."""
    recall_file = seed.seed_recall_file()

    assert recall_file["name"] == "install-memu"
    assert recall_file["track"] == "skill"
    assert "uninstall" in recall_file["description"].lower(), (
        "the description is what gets embedded — without the trigger word, a bare 'uninstall memU' cannot match"
    )
    assert "## Uninstall" in recall_file["content"]


class _FakeBackend:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def commit_results(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {"recall_files": kwargs.get("recall_files") or []}


@pytest.fixture
def backend(monkeypatch: pytest.MonkeyPatch) -> _FakeBackend:
    import memu.env

    fake = _FakeBackend()
    monkeypatch.setattr(memu.env, "build_agentic_memory_backend_from_env", lambda **_: fake)
    return fake


async def test_seed_writes_the_mirror_and_commits_to_the_store(
    backend: _FakeBackend, tmp_path: pathlib.Path
) -> None:
    mirror, result = await seed.seed(tmp_path)

    assert mirror == tmp_path / "skill" / "install-memu.md"
    assert read_recall_file(mirror, "skill") == seed.seed_recall_file(), (
        "the mirror must round-trip to the exact recall file the store received"
    )
    assert backend.calls == [{"recall_files": [seed.seed_recall_file()]}]
    assert result["recall_files"], "the caller reports what the store accepted"


async def test_reseeding_overwrites_in_place(backend: _FakeBackend, tmp_path: pathlib.Path) -> None:
    """A second install (same host or another sharing the store) refreshes, never stacks."""
    first, _ = await seed.seed(tmp_path)
    second, _ = await seed.seed(tmp_path)

    assert first == second
    assert [p.name for p in (tmp_path / "skill").iterdir()] == ["install-memu.md"]
    assert len(backend.calls) == 2, "each run re-commits — commit_results upserts by (track, name)"


def test_cli_registers_seed_skills() -> None:
    args = build_parser().parse_args(["seed-skills"])
    assert callable(args.handler)
    assert args.base_dir, "seed needs the working tree to place the mirror"
