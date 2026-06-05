from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from memu.app.markdown_context import ContextBucket


HARNESS_CONFIG_NAME = "harness.json"
HARNESS_CONFIG_VERSION = 1
DEFAULT_MAX_TEXT_CHARS = 4000
DEFAULT_CONTEXT_MAX_CHARS = 8000
DEFAULT_CONTEXT_FORMAT = "markdown"
CONTEXT_BUCKETS = {"memory", "soul", "skill"}
CONTEXT_FORMATS = {"markdown", "system", "messages", "json", "summary"}


def harness_config_path(repo_dir: str | Path, metadata_dir: str = ".memu") -> Path:
    return Path(repo_dir).resolve() / metadata_dir / HARNESS_CONFIG_NAME


def default_harness_config(
    *,
    exclude_patterns: Sequence[str] = (),
    max_text_chars: int = DEFAULT_MAX_TEXT_CHARS,
) -> dict[str, Any]:
    return {
        "version": HARNESS_CONFIG_VERSION,
        "compiler": {
            "exclude_patterns": [pattern for pattern in exclude_patterns if pattern],
            "max_text_chars": max_text_chars,
        },
        "context": {
            "max_chars": DEFAULT_CONTEXT_MAX_CHARS,
            "bucket_char_limits": {},
            "format": DEFAULT_CONTEXT_FORMAT,
        },
    }


def load_harness_config(repo_dir: str | Path, metadata_dir: str = ".memu") -> dict[str, Any]:
    config_path = harness_config_path(repo_dir, metadata_dir)
    if not config_path.exists():
        return {}
    try:
        loaded = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        msg = f"invalid harness config JSON at {config_path}: {exc}"
        raise SystemExit(msg) from exc
    if not isinstance(loaded, Mapping):
        msg = f"harness config root must be a JSON object: {config_path}"
        raise SystemExit(msg)
    validate_harness_config(loaded, config_path)
    return dict(loaded)


def try_load_harness_config(repo_dir: str | Path, metadata_dir: str = ".memu") -> tuple[dict[str, Any], str | None]:
    try:
        return load_harness_config(repo_dir, metadata_dir), None
    except SystemExit as exc:
        return {}, str(exc)


def validate_harness_config(config: Mapping[str, Any], config_path: Path) -> None:
    version = config.get("version", HARNESS_CONFIG_VERSION)
    if version != HARNESS_CONFIG_VERSION:
        msg = f"harness config version must be {HARNESS_CONFIG_VERSION}: {config_path}"
        raise SystemExit(msg)

    compiler = config_section(config, "compiler", config_path)
    config_string_list(compiler, "exclude_patterns", config_path)
    config_positive_int(
        compiler,
        "max_text_chars",
        DEFAULT_MAX_TEXT_CHARS,
        config_path=config_path,
    )

    context = config_section(config, "context", config_path)
    config_positive_int(
        context,
        "max_chars",
        DEFAULT_CONTEXT_MAX_CHARS,
        config_path=config_path,
    )
    config_context_buckets(context, config_path)
    config_bucket_char_limits(context, config_path)
    config_context_format(context, config_path)


def config_section(config: Mapping[str, Any], name: str, config_path: Path) -> Mapping[str, Any]:
    section = config.get(name, {})
    if section is None:
        return {}
    if not isinstance(section, Mapping):
        msg = f"harness config section {name!r} must be an object: {config_path}"
        raise SystemExit(msg)
    return section


def config_string_list(section: Mapping[str, Any], name: str, config_path: Path) -> list[str]:
    value = section.get(name, [])
    if value is None:
        return []
    if not isinstance(value, list):
        msg = f"harness config {name!r} must be a list of strings: {config_path}"
        raise SystemExit(msg)
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            msg = f"harness config {name!r} must be a list of strings: {config_path}"
            raise SystemExit(msg)
        clean = item.strip()
        if clean:
            result.append(clean)
    return result


def config_positive_int(
    section: Mapping[str, Any],
    name: str,
    default: int,
    *,
    config_path: Path,
) -> int:
    value = section.get(name, default)
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        msg = f"harness config {name!r} must be a positive integer: {config_path}"
        raise SystemExit(msg)
    return value


def positive_int_or_default(value: int | None, default: int, *, flag_name: str) -> int:
    if value is None:
        return default
    if value <= 0:
        msg = f"{flag_name} must be greater than 0"
        raise SystemExit(msg)
    return value


def arg_or_config_positive_int(
    arg_value: int | None,
    section: Mapping[str, Any],
    name: str,
    default: int,
    *,
    flag_name: str,
    config_path: Path,
) -> int:
    if arg_value is not None:
        return positive_int_or_default(arg_value, default, flag_name=flag_name)
    return config_positive_int(section, name, default, config_path=config_path)


def compiler_exclude_patterns(
    cli_patterns: Sequence[str] | None,
    compiler_section: Mapping[str, Any],
    config_path: Path,
) -> list[str]:
    if cli_patterns is not None:
        return [pattern for pattern in cli_patterns if pattern]
    return config_string_list(compiler_section, "exclude_patterns", config_path)


def config_context_buckets(section: Mapping[str, Any], config_path: Path) -> list[str]:
    buckets = config_string_list(section, "buckets", config_path)
    for bucket in buckets:
        if bucket not in CONTEXT_BUCKETS:
            msg = f"harness config context bucket must be one of memory, soul, skill: {config_path}"
            raise SystemExit(msg)
    return buckets


def config_bucket_char_limits(section: Mapping[str, Any], config_path: Path) -> dict[ContextBucket, int]:
    value = section.get("bucket_char_limits", {})
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        msg = f"harness config 'bucket_char_limits' must be an object: {config_path}"
        raise SystemExit(msg)
    limits: dict[ContextBucket, int] = {}
    for bucket, raw_limit in value.items():
        if not isinstance(bucket, str) or bucket not in CONTEXT_BUCKETS:
            msg = f"harness config bucket limit keys must be memory, soul, or skill: {config_path}"
            raise SystemExit(msg)
        if isinstance(raw_limit, bool) or not isinstance(raw_limit, int) or raw_limit <= 0:
            msg = f"harness config bucket limit values must be positive integers: {config_path}"
            raise SystemExit(msg)
        limits[cast(ContextBucket, bucket)] = raw_limit
    return limits


def config_context_format(section: Mapping[str, Any], config_path: Path) -> str:
    value = section.get("format", DEFAULT_CONTEXT_FORMAT)
    if value is None:
        return DEFAULT_CONTEXT_FORMAT
    if not isinstance(value, str) or value not in CONTEXT_FORMATS:
        msg = (
            "harness config context format must be one of "
            f"{', '.join(sorted(CONTEXT_FORMATS))}: {config_path}"
        )
        raise SystemExit(msg)
    return value


__all__ = [
    "CONTEXT_BUCKETS",
    "CONTEXT_FORMATS",
    "DEFAULT_CONTEXT_FORMAT",
    "DEFAULT_CONTEXT_MAX_CHARS",
    "DEFAULT_MAX_TEXT_CHARS",
    "HARNESS_CONFIG_NAME",
    "HARNESS_CONFIG_VERSION",
    "arg_or_config_positive_int",
    "compiler_exclude_patterns",
    "config_bucket_char_limits",
    "config_context_buckets",
    "config_context_format",
    "config_positive_int",
    "config_section",
    "config_string_list",
    "default_harness_config",
    "harness_config_path",
    "load_harness_config",
    "positive_int_or_default",
    "try_load_harness_config",
    "validate_harness_config",
]
