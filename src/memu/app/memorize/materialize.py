from __future__ import annotations

import contextlib
import json
import os
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import JsonValue

from memu.app.memorize.input import MemorizeInput, SkillInputItem, project_memory, project_skill


@dataclass(frozen=True)
class MaterializedConversation:
    """The transcript pair produced for one developer-supplied session."""

    memory_path: Path
    skill_path: Path


def _dump_item(item: SkillInputItem) -> dict[str, JsonValue]:
    optional_none = {
        name
        for name, field in type(item).model_fields.items()
        if getattr(item, name) is None and not field.is_required()
    }
    return item.model_dump(mode="json", exclude=optional_none)


def _serialize_items(items: Sequence[SkillInputItem]) -> str:
    return "".join(
        json.dumps(
            _dump_item(item),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        + "\n"
        for item in items
    )


def _atomic_write_text(path: Path, content: str) -> None:
    fd, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temporary_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary_name)
        raise


def materialize_memorize_input(
    memorize_input: MemorizeInput,
    out_dir: Path,
    *,
    session_index: int = 1,
    clear: bool = True,
) -> MaterializedConversation:
    """Write one session's memory and skill JSONL projections."""

    out_dir.mkdir(parents=True, exist_ok=True)
    if clear:
        for stale in out_dir.glob("*.jsonl"):
            stale.unlink()

    memory_path = out_dir / f"{session_index}.jsonl"
    skill_path = out_dir / f"{session_index}_full.jsonl"
    _atomic_write_text(memory_path, _serialize_items(project_memory(memorize_input)))
    _atomic_write_text(skill_path, _serialize_items(project_skill(memorize_input)))
    return MaterializedConversation(memory_path=memory_path, skill_path=skill_path)


def materialize_memorize_inputs(
    memorize_inputs: Sequence[MemorizeInput], out_dir: Path
) -> list[MaterializedConversation]:
    """Write numbered projections for a batch of sessions."""

    return [
        materialize_memorize_input(item, out_dir, session_index=index, clear=index == 1)
        for index, item in enumerate(memorize_inputs, start=1)
    ]
