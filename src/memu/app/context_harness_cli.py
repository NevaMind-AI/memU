from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from memu.app.cli_args import positive_float_arg, positive_int_arg, probability_arg
from memu.app.context_cli import _parse_bucket_char_limits, _render_pack, _write_output_text
from memu.app.context_harness import (
    ContextHarness,
    ContextHarnessRun,
    ContextHarnessSkillEvolutionResult,
    ContextHarnessSkillTraceResult,
)
from memu.app.folder import (
    EvolutionReviewApplyResult,
    FolderMemoryCompilerConfig,
    FolderHealthResult,
    FolderScaffoldResult,
    FolderStatusResult,
    scaffold_folder_memory_repository,
)
from memu.app.folder_cli import (
    _build_memory_service,
    _evolution_review_config,
    _parse_user_scope,
    _print_human_summary,
    _print_watch_event,
    _result_summary,
)
from memu.app.harness_config import (
    DEFAULT_CONTEXT_MAX_CHARS,
    DEFAULT_MAX_TEXT_CHARS,
    HARNESS_CONFIG_NAME,
    arg_or_config_positive_int,
    compiler_exclude_patterns,
    config_bucket_char_limits,
    config_context_buckets,
    config_context_format,
    config_section,
    default_harness_config,
    harness_config_path,
    load_harness_config,
    positive_int_or_default,
)
from memu.app.markdown_context import ContextBucket, MarkdownContextPack
from memu.app.skill_trace import SkillEvolutionProposal, SkillPromotionRecord, SkillTraceOutcome
from memu.app.skill_trace_cli import _parse_key_values, _parse_tool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memu-harness",
        description="Unified folder-backed context harness for memory, context, and self-evolving skills.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    common = _common_parent()
    context_options = _context_parent()

    init = subparsers.add_parser(
        "init",
        help="Create an empty Markdown memory repository layout.",
    )
    init.add_argument("repo_dir", help="Folder where the Markdown memory repository is stored.")
    init.add_argument("--source-folder", default=None, help="Optional uploaded folder to copy into raw_data/.")
    init.add_argument("--raw-data-dir", default="raw_data", help="Name of the raw data directory in output.")
    init.add_argument("--metadata-dir", default=".memu", help="Name of the metadata directory in output.")
    init.add_argument("--derived-dir", default="derived", help="Name of the derived evidence directory.")
    init.add_argument(
        "--max-text-chars",
        type=positive_int_arg,
        default=None,
        help="Default maximum text evidence chars per source file stored in .memu/harness.json.",
    )
    init.add_argument(
        "--exclude",
        action="append",
        default=None,
        metavar="GLOB",
        help="Exclude source files matching a posix glob during raw_data copy. Can be repeated.",
    )
    init.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    subparsers.add_parser(
        "ingest",
        parents=[common],
        help="Compile changed raw data through self-evolve review.",
    )
    subparsers.add_parser(
        "context",
        parents=[common, context_options],
        help="Build a context pack from the existing Markdown memory repository.",
    )
    subparsers.add_parser(
        "refresh",
        parents=[common, context_options],
        help="Compile changed raw data, then build a fresh context pack.",
    )
    subparsers.add_parser(
        "status",
        parents=[common],
        help="Inspect raw-data changes against the manifest without writing files.",
    )
    doctor = subparsers.add_parser(
        "doctor",
        help="Validate the Markdown memory repository layout and manifest without writing files.",
    )
    doctor.add_argument("repo_dir", help="Markdown memory repository to validate.")
    doctor.add_argument("--raw-data-dir", default="raw_data", help="Name of the raw data directory in output.")
    doctor.add_argument("--metadata-dir", default=".memu", help="Name of the metadata directory in output.")
    doctor.add_argument("--derived-dir", default="derived", help="Name of the derived evidence directory.")
    doctor.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    promote = subparsers.add_parser(
        "promote-skill",
        parents=[common],
        help="Append a durable manual skill note to skill.md.",
    )
    promote.add_argument("--title", required=True, help="Short name for the promoted skill.")
    promote.add_argument("--lesson", action="append", default=[], help="Reusable skill lesson. Can be repeated.")
    promote.add_argument("--action", action="append", default=[], help="Procedure step. Can be repeated.")
    promote.add_argument("--when", default="", help="When this skill should be used.")
    promote.add_argument("--source", default="", help="Optional source trace, task, or evidence path.")
    promote.add_argument("--tag", action="append", default=[], help="Skill tag. Can be repeated.")
    promote.add_argument(
        "--metadata",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Extra metadata stored on the promoted skill. Can be repeated.",
    )

    suggest = subparsers.add_parser(
        "suggest-skills",
        parents=[common],
        help="Suggest durable skills from raw skill traces without writing by default.",
    )
    suggest.add_argument("--limit", type=positive_int_arg, default=5, help="Maximum proposals to return.")
    suggest.add_argument(
        "--min-support",
        type=positive_int_arg,
        default=1,
        help="Minimum number of traces supporting a proposed skill.",
    )
    suggest.add_argument(
        "--promote",
        action="store_true",
        help="Write suggested skills into skill.md and skill/promoted/.",
    )

    review = subparsers.add_parser(
        "review-evolution",
        help="Approve or reject pending self-evolve patch proposals.",
    )
    review.add_argument("repo_dir", help="Markdown memory repository to review.")
    review.add_argument(
        "--proposal-id",
        action="append",
        default=None,
        help="Proposal ID to review. Can be repeated. Defaults to all pending proposals.",
    )
    review.add_argument("--reject", action="store_true", help="Reject matching pending proposals instead of approving.")
    review.add_argument("--reviewer", default="creator", help="Reviewer name recorded in the audit trail.")
    review.add_argument("--reason", default="", help="Review reason recorded in the audit trail.")
    review.add_argument("--raw-data-dir", default="raw_data", help="Name of the raw data directory in output.")
    review.add_argument("--metadata-dir", default=".memu", help="Name of the metadata directory in output.")
    review.add_argument("--derived-dir", default="derived", help="Name of the derived evidence directory.")
    review.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    trace = subparsers.add_parser(
        "trace",
        parents=[common],
        help="Record a skill-evolution trace under raw data and optionally recompile.",
    )
    trace.add_argument("--task", required=True, help="Task or situation this trace describes.")
    trace.add_argument(
        "--outcome",
        choices=("success", "failure", "partial", "unknown"),
        default="unknown",
        help="Outcome of the task.",
    )
    trace.add_argument("--summary", default="", help="Short summary of what happened.")
    trace.add_argument("--action", action="append", default=[], help="Action/workflow step. Can be repeated.")
    trace.add_argument("--lesson", action="append", default=[], help="Reusable skill lesson. Can be repeated.")
    trace.add_argument(
        "--tool",
        action="append",
        default=[],
        metavar="NAME[:success|failure][:score]",
        help="Tool usage summary. Can be repeated.",
    )
    trace.add_argument(
        "--metadata",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Extra metadata stored on the trace. Can be repeated.",
    )
    trace.add_argument("--no-recompile", action="store_true", help="Record the trace without recompiling.")

    watch = subparsers.add_parser(
        "watch",
        parents=[common],
        help="Keep polling raw data and recompile when files change.",
    )
    watch.add_argument("--poll-interval", type=positive_float_arg, default=2.0, help="Polling interval in seconds.")
    watch.add_argument(
        "--watch-max-runs",
        type=positive_int_arg,
        default=None,
        help="Stop watch mode after this many compile events. Mainly useful for automation.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        max_text_chars = positive_int_or_default(
            args.max_text_chars,
            DEFAULT_MAX_TEXT_CHARS,
            flag_name="--max-text-chars",
        )
        result = scaffold_folder_memory_repository(
            args.repo_dir,
            source_folder=args.source_folder,
            config=FolderMemoryCompilerConfig(
                raw_data_dir_name=args.raw_data_dir,
                metadata_dir_name=args.metadata_dir,
                derived_dir_name=args.derived_dir,
                exclude_patterns=tuple(args.exclude or []),
                max_text_chars=max_text_chars,
                use_memory_service=False,
            ),
        )
        config_path = _write_init_harness_config(result, args, max_text_chars=max_text_chars)
        if args.json:
            print(json.dumps(_scaffold_summary(result, config_path), indent=2, sort_keys=True))
        else:
            _print_scaffold_summary(result, config_path)
        return 0

    if args.command == "doctor":
        result = _doctor_health(args)
        if args.json:
            print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        else:
            _print_health_summary(result)
        return 0 if result.ok else 1

    if args.command == "review-evolution":
        harness = _review_harness(args)
        result = harness.review_evolution(
            proposal_ids=args.proposal_id,
            reviewer=args.reviewer,
            decision="rejected" if args.reject else "approved",
            reason=args.reason,
        )
        if args.json:
            print(json.dumps(_evolution_review_summary(result), indent=2, sort_keys=True))
        else:
            _print_evolution_review_summary(result)
        return 0

    harness = _build_harness(args)

    if args.command == "ingest":
        result = harness.ingest_sync()
        if args.json:
            print(json.dumps(_result_summary(result), indent=2, sort_keys=True))
        else:
            _print_human_summary(result)
        return 0

    if args.command == "context":
        pack = harness.build_context_pack(**_context_kwargs(args))
        _emit_context_output(_render_context_output(pack, args), args.output)
        return 0

    if args.command == "refresh":
        run = harness.refresh_context_sync(**_context_kwargs(args))
        if _context_output_format(args) == "json":
            _emit_context_output(json.dumps(_run_summary(run), indent=2, sort_keys=True) + "\n", args.output)
        else:
            _emit_context_output(_render_context_output(run.context_pack, args), args.output)
        return 0

    if args.command == "status":
        result = harness.status()
        if args.json:
            print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        else:
            _print_status_summary(result)
        return 0

    if args.command == "promote-skill":
        result = harness.promote_skill(
            title=args.title,
            lessons=list(args.lesson),
            actions=list(args.action),
            when_to_use=args.when,
            source=args.source,
            tags=list(args.tag),
            metadata=_parse_key_values(args.metadata, flag_name="--metadata"),
        )
        if args.json:
            print(json.dumps(_promotion_summary(result), indent=2, sort_keys=True))
        else:
            _print_promotion_summary(result)
        return 0

    if args.command == "suggest-skills":
        result = harness.evolve_skills(limit=args.limit, min_support=args.min_support, promote=args.promote)
        if args.json:
            print(json.dumps(_skill_evolution_summary(result), indent=2, sort_keys=True))
        else:
            _print_skill_evolution_summary(result)
        return 0

    if args.command == "trace":
        result = harness.record_skill_trace_sync(
            task=args.task,
            outcome=cast(SkillTraceOutcome, args.outcome),
            summary=args.summary,
            actions=list(args.action),
            tools=[_parse_tool(value) for value in args.tool],
            lessons=list(args.lesson),
            metadata=_parse_key_values(args.metadata, flag_name="--metadata"),
            recompile=not args.no_recompile,
        )
        if args.json:
            print(json.dumps(_trace_summary(result), indent=2, sort_keys=True))
        else:
            _print_trace_summary(result)
        return 0

    if args.command == "watch":
        harness.watch_sync(
            poll_interval=args.poll_interval,
            max_runs=args.watch_max_runs,
            on_event=lambda event: _print_watch_event(event, as_json=args.json),
        )
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


def _common_parent() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "paths",
        nargs="+",
        help=(
            "Either REPO_DIR, using REPO_DIR/raw_data as the source, or SOURCE_FOLDER REPO_DIR "
            "for an external raw-data folder."
        ),
    )
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
        default=None,
        help="Maximum text evidence chars per source file.",
    )
    parser.add_argument("--raw-data-dir", default="raw_data", help="Name of the raw data directory in output.")
    parser.add_argument("--metadata-dir", default=".memu", help="Name of the metadata directory in output.")
    parser.add_argument("--derived-dir", default="derived", help="Name of the derived evidence directory.")
    parser.add_argument(
        "--exclude",
        action="append",
        default=None,
        metavar="GLOB",
        help="Exclude source files matching a posix glob. Can be repeated.",
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
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

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
        default="profile,event,knowledge,behavior,skill,tool",
        help="Comma-separated MemoryService memory types to extract.",
    )
    return parser


def _context_parent() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
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
        help="Per-bucket context character budget, such as skill=2000. Can be repeated.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "system", "messages", "json", "summary"),
        default=None,
        help="Output format for context commands. --json is kept as a shortcut for --format json.",
    )
    parser.add_argument("--output", default=None, help="Optional file path to write the rendered context output.")
    return parser


def _write_init_harness_config(
    result: FolderScaffoldResult,
    args: argparse.Namespace,
    *,
    max_text_chars: int,
) -> Path:
    config_path = result.manifest_path.parent / HARNESS_CONFIG_NAME
    if config_path.exists():
        return config_path
    config_path.write_text(
        json.dumps(
            default_harness_config(
                exclude_patterns=args.exclude or (),
                max_text_chars=max_text_chars,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return config_path


def _context_section(args: argparse.Namespace) -> Mapping[str, Any]:
    config = cast(Mapping[str, Any], getattr(args, "_harness_config", {}))
    return config_section(config, "context", _context_config_path(args))


def _context_config_path(args: argparse.Namespace) -> Path:
    return cast(Path, getattr(args, "_harness_config_path", Path(".memu") / HARNESS_CONFIG_NAME))


def _build_harness(args: argparse.Namespace) -> ContextHarness:
    source_folder, repo_dir = _harness_paths(args)
    config_path = harness_config_path(repo_dir, args.metadata_dir)
    harness_config = load_harness_config(repo_dir, args.metadata_dir)
    setattr(args, "_harness_config", harness_config)
    setattr(args, "_harness_config_path", config_path)
    compiler_section = config_section(harness_config, "compiler", config_path)
    config = FolderMemoryCompilerConfig(
        raw_data_dir_name=args.raw_data_dir,
        metadata_dir_name=args.metadata_dir,
        derived_dir_name=args.derived_dir,
        exclude_patterns=tuple(compiler_exclude_patterns(args.exclude, compiler_section, config_path)),
        max_text_chars=arg_or_config_positive_int(
            args.max_text_chars,
            compiler_section,
            "max_text_chars",
            DEFAULT_MAX_TEXT_CHARS,
            flag_name="--max-text-chars",
            config_path=config_path,
        ),
        use_memory_service=args.use_memory_service,
        evolution_review=_evolution_review_config(args),
    )
    return ContextHarness(
        source_folder,
        repo_dir,
        memory_service=_build_memory_service(args),
        user=_parse_user_scope(args.user),
        compiler_config=config,
    )


def _doctor_health(args: argparse.Namespace) -> FolderHealthResult:
    config = FolderMemoryCompilerConfig(
        raw_data_dir_name=args.raw_data_dir,
        metadata_dir_name=args.metadata_dir,
        derived_dir_name=args.derived_dir,
        use_memory_service=False,
    )
    harness = ContextHarness(
        Path(args.repo_dir) / args.raw_data_dir,
        args.repo_dir,
        compiler_config=config,
    )
    return harness.health()


def _review_harness(args: argparse.Namespace) -> ContextHarness:
    config = FolderMemoryCompilerConfig(
        raw_data_dir_name=args.raw_data_dir,
        metadata_dir_name=args.metadata_dir,
        derived_dir_name=args.derived_dir,
        use_memory_service=False,
    )
    repo_dir = Path(args.repo_dir)
    return ContextHarness(
        repo_dir / args.raw_data_dir,
        repo_dir,
        compiler_config=config,
    )


def _harness_paths(args: argparse.Namespace) -> tuple[str, str]:
    if len(args.paths) == 1:
        repo_dir = args.paths[0]
        source_folder = str((Path(repo_dir) / args.raw_data_dir).resolve())
        return source_folder, repo_dir
    if len(args.paths) == 2:
        return args.paths[0], args.paths[1]
    msg = "commands expect either REPO_DIR or SOURCE_FOLDER REPO_DIR"
    raise SystemExit(msg)


def _context_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    context_section = _context_section(args)
    config_path = _context_config_path(args)
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
    return {
        "query": args.query,
        "buckets": buckets,
        "max_chars": arg_or_config_positive_int(
            args.max_chars,
            context_section,
            "max_chars",
            DEFAULT_CONTEXT_MAX_CHARS,
            flag_name="--max-chars",
            config_path=config_path,
        ),
        "include_generated": not args.no_generated,
        "include_manual": not args.no_manual,
        "bucket_char_limits": bucket_char_limits,
    }


def _context_output_format(args: argparse.Namespace) -> str:
    if args.json:
        return "json"
    if args.format is not None:
        return str(args.format)
    return config_context_format(_context_section(args), _context_config_path(args))


def _print_context_output(pack: MarkdownContextPack, args: argparse.Namespace) -> None:
    _emit_context_output(_render_context_output(pack, args), None)


def _render_context_output(pack: MarkdownContextPack, args: argparse.Namespace) -> str:
    return _render_pack(pack, _context_output_format(args))


def _emit_context_output(text: str, output_path: str | None) -> None:
    if output_path:
        _write_output_text(text, output_path)
        return
    print(text, end="")


def _run_summary(run: ContextHarnessRun) -> dict[str, Any]:
    return {
        "compile": _result_summary(run.compile_result),
        "context": run.context_pack.to_dict(),
    }


def _trace_summary(result: ContextHarnessSkillTraceResult) -> dict[str, Any]:
    return {
        "raw_data_dir": str(result.record.raw_data_dir),
        "trace_path": str(result.record.trace_path),
        "task": result.record.trace.task,
        "outcome": result.record.trace.outcome,
        "compiled": _result_summary(result.compile_result) if result.compile_result is not None else None,
    }


def _skill_evolution_summary(result: ContextHarnessSkillEvolutionResult) -> dict[str, Any]:
    return {
        "proposal_count": len(result.proposals),
        "promoted_count": len(result.promotions),
        "proposals": [_proposal_summary(proposal) for proposal in result.proposals],
        "promotions": [_promotion_summary(promotion) for promotion in result.promotions],
    }


def _proposal_summary(proposal: SkillEvolutionProposal) -> dict[str, Any]:
    return proposal.to_dict()


def _scaffold_summary(result: FolderScaffoldResult, config_path: Path | None = None) -> dict[str, Any]:
    return {
        "output_dir": str(result.output_dir),
        "raw_data_dir": str(result.raw_data_dir),
        "manifest_path": str(result.manifest_path),
        "config_path": str(config_path) if config_path is not None else None,
        "created": result.created,
        "copied": result.copied,
    }


def _print_scaffold_summary(result: FolderScaffoldResult, config_path: Path | None = None) -> None:
    summary = _scaffold_summary(result, config_path)
    print("memU harness repository initialized")
    print(f"  output: {summary['output_dir']}")
    print(f"  raw_data: {summary['raw_data_dir']}")
    print(f"  manifest: {summary['manifest_path']}")
    if summary["config_path"]:
        print(f"  config: {summary['config_path']}")
    print(f"  created: {len(result.created)}")
    print(f"  copied: {len(result.copied)}")


def _print_status_summary(result: FolderStatusResult) -> None:
    counts = result.to_dict()["counts"]
    print("memU harness status")
    print(f"  source: {result.source_dir}")
    print(f"  output: {result.output_dir}")
    print(f"  new: {counts['new']}")
    print(f"  changed: {counts['changed']}")
    print(f"  removed: {counts['removed']}")
    print(f"  unchanged: {counts['unchanged']}")
    for state in ("new", "changed", "removed"):
        paths = getattr(result, state)
        if paths:
            print(f"  {state}: {', '.join(paths)}")


def _print_health_summary(result: FolderHealthResult) -> None:
    print("memU harness health")
    print(f"  output: {result.output_dir}")
    print(f"  ok: {result.ok}")
    print(f"  errors: {result.error_count}")
    print(f"  warnings: {result.warning_count}")
    for issue in result.issues:
        location = f" [{issue.path}]" if issue.path else ""
        print(f"  - {issue.severity}: {issue.code}{location} - {issue.message}")


def _promotion_summary(result: SkillPromotionRecord) -> dict[str, Any]:
    return {
        "repo_dir": str(result.repo_dir),
        "skill_path": str(result.skill_path),
        "card_path": str(result.card_path) if result.card_path is not None else None,
        "title": result.title,
        "promoted_at": result.promoted_at,
    }


def _evolution_review_summary(result: EvolutionReviewApplyResult) -> dict[str, Any]:
    return {
        "output_dir": str(result.output_dir),
        "manifest_path": str(result.manifest_path),
        "reviewed_count": len(result.reviewed),
        "applied_proposal_ids": list(result.applied_proposal_ids),
        "removed": list(result.removed),
        "entry_count": len(result.entries),
        "reviews": [review.to_dict() for review in result.reviewed],
    }


def _print_promotion_summary(result: SkillPromotionRecord) -> None:
    summary = _promotion_summary(result)
    print("memU harness skill promoted")
    print(f"  skill: {summary['title']}")
    print(f"  path: {summary['skill_path']}")
    print(f"  promoted_at: {summary['promoted_at']}")


def _print_evolution_review_summary(result: EvolutionReviewApplyResult) -> None:
    summary = _evolution_review_summary(result)
    print("memU harness evolution review applied")
    print(f"  manifest: {summary['manifest_path']}")
    print(f"  reviewed: {summary['reviewed_count']}")
    print(f"  applied: {len(result.applied_proposal_ids)}")
    print(f"  removed: {len(result.removed)}")
    print(f"  entries: {summary['entry_count']}")


def _print_skill_evolution_summary(result: ContextHarnessSkillEvolutionResult) -> None:
    print("memU harness skill suggestions")
    print(f"  proposals: {len(result.proposals)}")
    print(f"  promoted: {len(result.promotions)}")
    for proposal in result.proposals:
        print(f"  - {proposal.title} (support={proposal.support_count}, score={proposal.score})")
        if proposal.lessons:
            print(f"    lesson: {proposal.lessons[0]}")
        if proposal.sources:
            print(f"    sources: {', '.join(proposal.sources)}")


def _print_trace_summary(result: ContextHarnessSkillTraceResult) -> None:
    summary = _trace_summary(result)
    print("memU harness skill trace recorded")
    print(f"  trace: {summary['trace_path']}")
    print(f"  task: {summary['task']}")
    print(f"  outcome: {summary['outcome']}")
    if summary["compiled"] is not None:
        print(f"  compiled entries: {summary['compiled']['entry_count']}")


if __name__ == "__main__":
    raise SystemExit(main())
