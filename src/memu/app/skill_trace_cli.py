from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from typing import Any, cast

from memu.app.folder import FolderMemoryCompilerConfig, compile_folder_to_markdown_sync
from memu.app.skill_trace import SkillToolTrace, SkillTraceOutcome, record_skill_trace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memu-skill-trace",
        description="Record an agent/tool execution trace into raw_data for self-evolving skills.",
    )
    parser.add_argument("raw_data_dir", help="Raw data folder where skill_traces/ will be written.")
    parser.add_argument("--task", required=True, help="Task or situation this trace describes.")
    parser.add_argument(
        "--outcome",
        choices=("success", "failure", "partial", "unknown"),
        default="unknown",
        help="Outcome of the task.",
    )
    parser.add_argument("--summary", default="", help="Short summary of what happened.")
    parser.add_argument("--action", action="append", default=[], help="Action/workflow step. Can be repeated.")
    parser.add_argument("--lesson", action="append", default=[], help="Reusable skill lesson. Can be repeated.")
    parser.add_argument(
        "--tool",
        action="append",
        default=[],
        metavar="NAME[:success|failure][:score]",
        help="Tool usage summary. Can be repeated.",
    )
    parser.add_argument(
        "--metadata",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Extra metadata stored on the trace. Can be repeated.",
    )
    parser.add_argument(
        "--output-folder",
        default=None,
        help="Optional memory repo folder to recompile after recording the trace.",
    )
    parser.add_argument("--json", action="store_true", help="Print a machine-readable JSON summary.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    record = record_skill_trace(
        args.raw_data_dir,
        task=args.task,
        outcome=cast(SkillTraceOutcome, args.outcome),
        summary=args.summary,
        actions=list(args.action),
        tools=[_parse_tool(value) for value in args.tool],
        lessons=list(args.lesson),
        metadata=_parse_key_values(args.metadata, flag_name="--metadata"),
    )
    compile_summary: dict[str, Any] | None = None
    if args.output_folder:
        result = compile_folder_to_markdown_sync(
            args.raw_data_dir,
            args.output_folder,
            config=FolderMemoryCompilerConfig(use_memory_service=False),
        )
        compile_summary = {
            "processed": result.processed,
            "skipped": result.skipped,
            "removed": result.removed,
            "entry_count": len(result.entries),
        }

    summary = {
        "raw_data_dir": str(record.raw_data_dir),
        "trace_path": str(record.trace_path),
        "task": record.trace.task,
        "outcome": record.trace.outcome,
        "compiled": compile_summary,
    }
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print("memU skill trace recorded")
        print(f"  trace: {summary['trace_path']}")
        print(f"  task: {summary['task']}")
        print(f"  outcome: {summary['outcome']}")
        if compile_summary is not None:
            print(f"  compiled entries: {compile_summary['entry_count']}")
    return 0


def _parse_tool(value: str) -> SkillToolTrace:
    parts = value.split(":")
    name = parts[0].strip()
    if not name:
        msg = "--tool values must start with a tool name"
        raise SystemExit(msg)
    success = True
    score: float | None = None
    if len(parts) >= 2 and parts[1].strip():
        status = parts[1].strip().lower()
        if status not in {"success", "failure"}:
            msg = "--tool status must be success or failure"
            raise SystemExit(msg)
        success = status == "success"
    if len(parts) >= 3 and parts[2].strip():
        score = float(parts[2].strip())
    return SkillToolTrace(name=name, success=success, score=score)


def _parse_key_values(values: Sequence[str], *, flag_name: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in values:
        key, sep, value = raw.partition("=")
        if not sep or not key.strip():
            msg = f"{flag_name} values must be KEY=VALUE, got: {raw!r}"
            raise SystemExit(msg)
        result[key.strip()] = value
    return result


if __name__ == "__main__":
    raise SystemExit(main())
