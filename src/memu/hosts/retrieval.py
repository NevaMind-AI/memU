"""The inject seam — one retrieval call, shared by every host adapter.

ADR 0008 gives each host two seams. *Record* genuinely differs per host: each
writes its session log its own way, which is what
:class:`~memu.hosts.base.TranscriptSource` exists to absorb. *Inject* does not —
whatever a host's prompt hook looks like, the retrieval it triggers is the same
query against the same store. So it lives here once, and each host CLI registers
it under its own binary (``memu-codex retrieve``, and whatever comes next),
because that binary is what the host's hook can reliably invoke.

This wraps :meth:`AgenticMixin.progressive_retrieve`: LLM-free, the query is
embedded once, and the segment/file/resource layers come back ranked. No
intention routing, sufficiency checks, or summarization — cheap enough to run
on a per-turn hook.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from memu.env import build_agentic_memory_backend_from_env
from memu.hosts.bridging.layout import BASE_DIR, TRACK_DIRS
from memu.hosts.bridging.recall_files import recall_file_path


async def retrieve(query: str, where: dict[str, Any] | None = None) -> dict[str, Any]:
    """Retrieve against the configured backend. Returns ``segments``/``files``/``resources``.

    Embeddings are already stripped from the hits, so the result is safe to print.
    :func:`_shape_for_agent` then reshapes the raw store records into the
    progressive form the standing instruction promises (see
    :mod:`memu.hosts.instruction`).
    """
    backend = build_agentic_memory_backend_from_env()
    result: dict[str, Any] = await backend.progressive_retrieve(query, where=where)
    return _shape_for_agent(result)


def _mirror_path(base: Path, track: Any, name: Any) -> Path | None:
    """The mirror path a recall file *should* live at, or ``None`` if unlocatable.

    Unlocatable means the file's track has no mirror directory (only
    ``memory``/``skill`` are mirrored) or it has no name — in either case there
    is no path to hand the agent, so the caller falls back to inline content.
    """
    subdir = TRACK_DIRS.get(track or "")
    if subdir is None or not name:
        return None
    return recall_file_path(base, subdir, str(name))


def _source_label(track: Any, name: Any) -> str | None:
    """A stable, human-readable id for a recall file: ``<track>/<name>``.

    What a segment points back to and what the agent matches against the
    ``files`` layer. The track prefix disambiguates a bare name (which can
    collide across tracks). It is deliberately *not* a filesystem path — the
    openable location is the file's ``path`` — so a segment never carries a
    location that may not exist on disk.
    """
    if not name:
        return None
    return f"{track}/{name}" if track else str(name)


def _shape_for_agent(result: dict[str, Any]) -> dict[str, Any]:
    """Reshape raw retrieval records into the agent-facing progressive form.

    Matching the instruction's contract that files and resources come back as
    *a location plus a summary* rather than full text:

    * ``files`` shed their ``content``: when the on-disk mirror
      (``~/.memu/<track>/<name>.md``) exists, they carry a ``path`` to it; when
      it does not — the user owns that tree and may delete it — they keep the
      ``content`` inline and emit *no* ``path``, so the agent never sees a
      location that isn't there. The internal ``resource_urls`` link list is
      dropped: the standing instruction never names it, so it is noise.
    * ``segments`` swap the internal ``recall_file_id`` UUID for ``source_file``,
      the ``<track>/<name>`` id of their parent file — an identifier for finding
      the fuller document in ``files``, not a path to open (that is the file's
      job, which degrades cleanly to inline content).
    * ``resources`` collapse the duplicated ``url``/``local_path`` (``commit`` is
      the only writer and sets them equal) down to a single ``path``.
    """
    base = Path(os.path.expanduser(BASE_DIR))

    file_labels: dict[str, str | None] = {}
    for file in result.get("files", []):
        file_labels[file.get("id")] = _source_label(file.get("track"), file.get("name"))

        path = _mirror_path(base, file.get("track"), file.get("name"))
        content = file.pop("content", None)
        file.pop("resource_urls", None)
        if path is not None and path.exists():
            # The mirror is on disk: hand over the openable location, not the text.
            file["path"] = str(path)
        else:
            # Unlocatable, or the mirror is gone: keep the text inline and emit no
            # dead path, so the agent never reasons about a file that isn't there.
            file["content"] = content

    for segment in result.get("segments", []):
        fid = segment.pop("recall_file_id", None)
        segment["source_file"] = file_labels.get(fid)

    for resource in result.get("resources", []):
        resource.pop("local_path", None)
        if "url" in resource:
            resource["path"] = resource.pop("url")

    return result


async def _cmd_retrieve(args: argparse.Namespace) -> int:
    result = await retrieve(args.query)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


def register(sub: Any) -> None:
    """Add the ``retrieve`` subcommand to a host CLI's subparsers."""
    parser = sub.add_parser(
        "retrieve",
        help="LLM-free single-shot retrieval over memory, skills, and resources (what the inject hook runs)",
    )
    parser.add_argument("query", help="Natural-language query")
    parser.set_defaults(handler=_cmd_retrieve)
