from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from memu.app.cli_args import positive_int_arg
from memu.app.harness_config import (
    DEFAULT_CONTEXT_MAX_CHARS,
    arg_or_config_positive_int,
    config_bucket_char_limits,
    config_context_buckets,
    config_context_format,
    config_section,
    harness_config_path,
    load_harness_config,
)
from memu.app.markdown_context import ContextBucket, MarkdownContextPack, build_markdown_context_pack


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memu-context",
        description="Build an agent-ready context pack from a memU Markdown memory repository.",
    )
    parser.add_argument("repo_dir", help="Folder containing memory.md, soul.md, skill.md, and .memu/manifest.json.")
    parser.add_argument("--query", default=None, help="Optional query used for lightweight relevance ranking.")
    parser.add_argument(
        "--max-chars",
        type=positive_int_arg,
        default=None,
        help="Maximum approximate context characters.",
    )
    parser.add_argument(
        "--bucket",
        action="append",
        choices=("memory", "soul", "skill"),
        default=None,
        help="Bucket to include. Can be repeated. Defaults to all buckets.",
    )
    parser.add_argument("--no-generated", action="store_true", help="Exclude generated manifest entries.")
    parser.add_argument("--no-manual", action="store_true", help="Exclude manual Markdown outside generated blocks.")
    parser.add_argument(
        "--bucket-max",
        action="append",
        default=None,
        metavar="BUCKET=CHARS",
        help="Per-bucket context character budget, such as soul=1000. Can be repeated.",
    )
    parser.add_argument("--json", action="store_true", help="Print a machine-readable JSON context pack.")
    parser.add_argument(
        "--format",
        choices=("markdown", "system", "messages", "json", "summary"),
        default=None,
        help="Output format. --json is kept as a shortcut for --format json.",
    )
    parser.add_argument("--output", default=None, help="Optional file path to write the rendered context output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config_path = harness_config_path(args.repo_dir)
    harness_config = load_harness_config(args.repo_dir)
    context_section = config_section(harness_config, "context", config_path)
    bucket_values = (
        list(args.bucket)
        if args.bucket is not None
        else config_context_buckets(context_section, config_path)
    )
    buckets = [cast(ContextBucket, bucket) for bucket in bucket_values] if bucket_values else None
    bucket_char_limits = (
        _parse_bucket_char_limits(args.bucket_max)
        if args.bucket_max is not None
        else config_bucket_char_limits(context_section, config_path)
    )
    pack = build_markdown_context_pack(
        args.repo_dir,
        query=args.query,
        buckets=buckets,
        max_chars=arg_or_config_positive_int(
            args.max_chars,
            context_section,
            "max_chars",
            DEFAULT_CONTEXT_MAX_CHARS,
            flag_name="--max-chars",
            config_path=config_path,
        ),
        include_generated=not args.no_generated,
        include_manual=not args.no_manual,
        bucket_char_limits=bucket_char_limits,
    )
    output_format = _context_output_format(args, context_section, config_path)
    _emit_output(_render_pack(pack, output_format), args.output)
    return 0


def _context_output_format(args: argparse.Namespace, context_section: Any, config_path: Path) -> str:
    if args.json:
        return "json"
    if args.format is not None:
        return str(args.format)
    return config_context_format(context_section, config_path)


def _print_pack(pack: MarkdownContextPack, output_format: str) -> None:
    _emit_output(_render_pack(pack, output_format), None)


def _render_pack(pack: MarkdownContextPack, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(pack.to_dict(), indent=2, sort_keys=True) + "\n"
    if output_format == "summary":
        return json.dumps(pack.to_summary(), indent=2, sort_keys=True) + "\n"
    if output_format == "messages":
        return json.dumps(pack.to_messages(), indent=2, sort_keys=True) + "\n"
    if output_format == "system":
        return pack.to_system_prompt()
    return pack.to_markdown()


def _emit_output(text: str, output_path: str | None) -> None:
    if output_path:
        _write_output_text(text, output_path)
        return
    print(text, end="")


def _write_output_text(text: str, output_path: str) -> None:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _parse_bucket_char_limits(values: Sequence[str]) -> dict[ContextBucket, int]:
    limits: dict[ContextBucket, int] = {}
    for value in values:
        bucket, sep, raw_limit = value.partition("=")
        if not sep:
            msg = f"--bucket-max expects BUCKET=CHARS, got {value!r}"
            raise SystemExit(msg)
        clean_bucket = bucket.strip()
        if clean_bucket not in {"memory", "soul", "skill"}:
            msg = f"unknown bucket for --bucket-max: {clean_bucket}"
            raise SystemExit(msg)
        try:
            limit = int(raw_limit)
        except ValueError as exc:
            msg = f"--bucket-max value must be an integer: {value!r}"
            raise SystemExit(msg) from exc
        if limit <= 0:
            msg = "--bucket-max values must be greater than 0"
            raise SystemExit(msg)
        limits[cast(ContextBucket, clean_bucket)] = limit
    return limits


if __name__ == "__main__":
    raise SystemExit(main())
