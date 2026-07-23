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

from memu.env import build_service_from_env
from memu.hosts.bridging.layout import BASE_DIR, TRACK_DIRS
from memu.hosts.bridging.recall_files import recall_file_path


async def retrieve(query: str, where: dict[str, Any] | None = None) -> dict[str, Any]:
    """Retrieve against the configured store. Returns ``segments``/``files``/``resources``.

    Embeddings are already stripped from the hits, so the result is safe to print.
    :func:`_shape_for_agent` then reshapes the raw store records into the
    progressive form the standing instruction promises (see
    :mod:`memu.hosts.instruction`).
    """
    service = build_service_from_env()
    result: dict[str, Any] = await service.progressive_retrieve(query, where=where)
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


def _shape_for_agent(result: dict[str, Any]) -> dict[str, Any]:
    """Reshape raw retrieval records into the agent-facing progressive form.

    Matching the instruction's contract that files and resources come back as
    *a location plus a summary* rather than full text:

    * ``files`` shed their ``content`` in favour of a ``path`` to the on-disk
      mirror (``~/.memu/<track>/<name>.md``). The mirror is written by
      ``commit`` but is not guaranteed to survive — the user owns that tree — so
      when it is missing the ``content`` is kept inline and the result stays
      self-sufficient. The internal ``resource_urls`` link list is dropped: the
      standing instruction never names it, so it is noise to the agent.
    * ``segments`` swap the internal ``recall_file_id`` UUID for ``source_file``:
      the same ``path`` its parent file reports, so provenance is both
      human-meaningful and directly openable, with no cross-referencing a UUID.
    * ``resources`` collapse the duplicated ``url``/``local_path`` (``commit`` is
      the only writer and sets them equal) down to a single ``path``.
    """
    base = Path(os.path.expanduser(BASE_DIR))

    file_paths: dict[str, str] = {}
    for file in result.get("files", []):
        path = _mirror_path(base, file.get("track"), file.get("name"))
        content = file.pop("content", None)
        _ = file.pop("resource_urls", None)
        if path is not None:
            file["path"] = str(path)
            file_paths[file.get("id")] = str(path)
        if path is None or not path.exists():
            # Unlocatable, or the mirror is gone: keep the text so the agent
            # still has it even though there is no file to open.
            file["content"] = content

    for segment in result.get("segments", []):
        fid = segment.pop("recall_file_id", None)
        segment["source_file"] = file_paths.get(fid)

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
