from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from memu.app.cli_args import positive_float_arg, positive_int_arg, probability_arg
from memu.app.folder import (
    FolderCompileResult,
    FolderMemoryCompilerConfig,
    FolderWatchEvent,
    compile_folder_to_markdown_sync,
    watch_folder_to_markdown_sync,
)
from memu.app.self_evolve import EvolutionReviewConfig
from memu.app.settings import default_api_key_env


DEFAULT_FOLDER_MEMORY_TYPES = ("profile", "event", "knowledge", "behavior", "skill", "tool")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memu-folder",
        description="Compile a raw data folder through self-evolve review into a Markdown memory repository.",
    )
    parser.add_argument("source_folder", help="Folder containing raw source files to compile.")
    parser.add_argument("output_folder", help="Folder where the Markdown memory repository will be written.")
    parser.add_argument(
        "--user",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="User scope value passed through to MemoryService. Can be repeated.",
    )
    parser.add_argument(
        "--max-text-chars",
        type=positive_int_arg,
        default=4000,
        help="Maximum text evidence chars per source file.",
    )
    parser.add_argument("--raw-data-dir", default="raw_data", help="Name of the raw data directory in output.")
    parser.add_argument("--metadata-dir", default=".memu", help="Name of the metadata directory in output.")
    parser.add_argument("--derived-dir", default="derived", help="Name of the derived evidence directory.")
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="Exclude source files matching a posix glob. Can be repeated.",
    )
    parser.add_argument("--json", action="store_true", help="Print a machine-readable JSON summary.")
    parser.add_argument("--watch", action="store_true", help="Keep polling the source folder and recompile on changes.")
    parser.add_argument(
        "--poll-interval",
        type=positive_float_arg,
        default=2.0,
        help="Polling interval in seconds for --watch.",
    )
    parser.add_argument(
        "--watch-max-runs",
        type=positive_int_arg,
        default=None,
        help="Stop watch mode after this many compile events. Mainly useful for automation.",
    )
    parser.add_argument(
        "--require-creator-review",
        action="store_true",
        help="Create Evolution Instructions and Patch Proposals without auto-applying them.",
    )
    parser.add_argument(
        "--min-evolution-confidence",
        type=probability_arg,
        default=0.0,
        help="Minimum confidence required for auto-approved evolution patches.",
    )

    service = parser.add_argument_group("MemoryService extraction")
    service.add_argument(
        "--use-memory-service",
        action="store_true",
        help="Use MemoryService and configured LLMs for richer multimodal extraction.",
    )
    service.add_argument("--provider", default="openai", help="LLM provider for MemoryService.")
    service.add_argument("--client-backend", default="sdk", choices=("sdk", "httpx", "lazyllm_backend"))
    service.add_argument("--base-url", default=None, help="Optional LLM API base URL.")
    service.add_argument("--api-key", default=None, help="LLM API key. Defaults to the selected API key env var.")
    service.add_argument(
        "--api-key-env",
        default=None,
        help="Environment variable to read the API key from. Defaults to the provider's standard env var.",
    )
    service.add_argument("--chat-model", default="gpt-4o-mini", help="Chat/vision model for extraction.")
    service.add_argument("--embed-model", default="text-embedding-3-small", help="Embedding model for indexing.")
    service.add_argument(
        "--memory-types",
        default=",".join(DEFAULT_FOLDER_MEMORY_TYPES),
        help="Comma-separated MemoryService memory types to extract.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = FolderMemoryCompilerConfig(
        raw_data_dir_name=args.raw_data_dir,
        metadata_dir_name=args.metadata_dir,
        derived_dir_name=args.derived_dir,
        exclude_patterns=tuple(args.exclude),
        max_text_chars=args.max_text_chars,
        use_memory_service=args.use_memory_service,
        evolution_review=_evolution_review_config(args),
    )
    memory_service = _build_memory_service(args)
    user = _parse_user_scope(args.user)
    if args.watch:
        watch_folder_to_markdown_sync(
            args.source_folder,
            args.output_folder,
            memory_service=memory_service,
            user=user,
            config=config,
            poll_interval=args.poll_interval,
            max_runs=args.watch_max_runs,
            on_event=lambda event: _print_watch_event(event, as_json=args.json),
        )
    else:
        result = compile_folder_to_markdown_sync(
            args.source_folder,
            args.output_folder,
            memory_service=memory_service,
            user=user,
            config=config,
        )
        if args.json:
            print(json.dumps(_result_summary(result), indent=2, sort_keys=True))
        else:
            _print_human_summary(result)
    return 0


def _build_memory_service(args: argparse.Namespace) -> Any | None:
    if not args.use_memory_service:
        return None

    from memu.app.service import MemoryService

    llm_profile = _llm_profile_from_args(args)

    return MemoryService(
        llm_profiles={"default": llm_profile},
        memorize_config={"memory_types": _parse_csv(args.memory_types)},
    )


def _llm_profile_from_args(args: argparse.Namespace) -> dict[str, Any]:
    api_key_env = args.api_key_env or default_api_key_env(args.provider)
    api_key = args.api_key or os.getenv(api_key_env) or api_key_env
    llm_profile: dict[str, Any] = {
        "provider": args.provider,
        "client_backend": args.client_backend,
        "api_key": api_key,
        "chat_model": args.chat_model,
        "embed_model": args.embed_model,
    }
    if args.base_url:
        llm_profile["base_url"] = args.base_url

    return llm_profile


def _parse_user_scope(values: Sequence[str]) -> dict[str, str]:
    user: dict[str, str] = {}
    for raw in values:
        key, sep, value = raw.partition("=")
        if not sep or not key.strip():
            msg = f"--user values must be KEY=VALUE, got: {raw!r}"
            raise SystemExit(msg)
        user[key.strip()] = value
    return user


def _parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _evolution_review_config(args: argparse.Namespace) -> EvolutionReviewConfig:
    if args.min_evolution_confidence < 0 or args.min_evolution_confidence > 1:
        msg = "--min-evolution-confidence must be between 0 and 1"
        raise SystemExit(msg)
    return EvolutionReviewConfig(
        auto_approve=not args.require_creator_review,
        min_confidence=args.min_evolution_confidence,
    )


def _result_summary(result: FolderCompileResult) -> dict[str, Any]:
    return {
        "output_dir": str(result.output_dir),
        "raw_data_dir": str(result.raw_data_dir),
        "manifest_path": str(result.manifest_path),
        "processed": result.processed,
        "skipped": result.skipped,
        "removed": result.removed,
        "entry_count": len(result.entries),
        "evolution_instruction_count": len(result.evolution_instructions),
        "patch_proposal_count": len(result.patch_proposals),
        "review_decision_count": len(result.review_decisions),
        "entries_by_bucket": {
            "memory": sum(1 for entry in result.entries if entry.bucket == "memory"),
            "soul": sum(1 for entry in result.entries if entry.bucket == "soul"),
            "skill": sum(1 for entry in result.entries if entry.bucket == "skill"),
        },
    }


def _print_human_summary(result: FolderCompileResult) -> None:
    summary = _result_summary(result)
    print("memU folder compile complete")
    print(f"  output: {summary['output_dir']}")
    print(f"  raw_data: {summary['raw_data_dir']}")
    print(f"  manifest: {summary['manifest_path']}")
    print(f"  processed: {len(result.processed)}")
    print(f"  skipped: {len(result.skipped)}")
    print(f"  removed: {len(result.removed)}")
    print(f"  entries: {summary['entry_count']} {summary['entries_by_bucket']}")
    print(
        "  evolution: "
        f"instructions={summary['evolution_instruction_count']} "
        f"proposals={summary['patch_proposal_count']} "
        f"reviews={summary['review_decision_count']}"
    )


def _watch_event_summary(event: FolderWatchEvent) -> dict[str, Any]:
    summary = _result_summary(event.result)
    summary["iteration"] = event.iteration
    summary["reason"] = event.reason
    if event.status is not None:
        status = event.status.to_dict()
        summary["delta"] = {
            "counts": status["counts"],
            "new": status["new"],
            "changed": status["changed"],
            "removed": status["removed"],
        }
    return summary


def _print_watch_event(event: FolderWatchEvent, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(_watch_event_summary(event), sort_keys=True), flush=True)
        return
    print(f"memU folder watch event #{event.iteration}: {event.reason}", flush=True)
    if event.status is not None:
        counts = event.status.to_dict()["counts"]
        print(
            f"  delta: new={counts['new']} changed={counts['changed']} removed={counts['removed']}",
            flush=True,
        )
    _print_human_summary(event.result)


if __name__ == "__main__":
    raise SystemExit(main())
