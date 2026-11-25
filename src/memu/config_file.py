"""Shared TOML configuration, with one-time migration of legacy dotenv files.

Environment names remain the internal API. The public file uses short TOML keys.
All writers merge under the same process lock and atomically replace the file.
"""

from __future__ import annotations

import contextlib
import os
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import tomlkit
from filelock import FileLock
from tomlkit.toml_document import TOMLDocument

from memu.config_schema import KEYS, env_value, typed_value
from memu.env import read_config

CONFIG_TOML = "~/.memu/config.toml"
LEGACY_CONFIG = "~/.memu/config.env"
_TEMPLATE = Path(__file__).with_name("config_template.toml")


def legacy_path() -> Path:
    return Path(os.path.expanduser(os.environ.get("MEMU_CONFIG_ENV", LEGACY_CONFIG)))


def config_path() -> Path:
    """Keep custom legacy locations local; MEMU_CONFIG explicitly selects TOML."""
    explicit = os.environ.get("MEMU_CONFIG")
    if explicit:
        return Path(os.path.expanduser(explicit))
    if "MEMU_CONFIG_ENV" in os.environ:
        source = legacy_path()
        target = source.with_suffix(".toml")
        return target if target != source else source.with_suffix(".migrated.toml")
    return Path(CONFIG_TOML).expanduser()


def active_path() -> Path:
    """Report the file actually in use, including a failed-migration fallback."""
    target = config_path()
    return legacy_path() if not target.exists() and legacy_path().is_file() else target


def state_path() -> Path:
    return config_path().with_suffix(".state.toml")


def _legacy_read() -> dict[str, str]:
    try:
        text, _ = read_config(legacy_path())
    except FileNotFoundError:
        return {}
    values: dict[str, str] = {}
    for raw in text.splitlines():
        key, value = _split(raw)
        if key:
            values[key] = value.strip().strip("\"'")
    return values


def _load(path: Path) -> TOMLDocument:
    text, _ = read_config(path)
    return tomlkit.parse(text)


def _set(document: Any, dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    for part in parts[:-1]:
        if part not in document:
            document[part] = tomlkit.table()
        document = document[part]
    document[parts[-1]] = value


def _flatten(document: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, dotted in KEYS.items():
        value: Any = document
        for part in dotted.split("."):
            if not isinstance(value, Mapping) or part not in value:
                break
            value = value[part]
        else:
            # tomlkit scalars are wrappers; unwrap before checking native types.
            if hasattr(value, "unwrap"):
                value = value.unwrap()
            result[key] = env_value(key, value)
    legacy = document.get("legacy", {})
    if not isinstance(legacy, Mapping) or any(not isinstance(v, str) for v in legacy.values()):
        raise ValueError("legacy must contain string values")  # noqa: TRY003
    # Explicit TOML fields always win over preserved extension / compatibility keys.
    return {**legacy, **result}


def _new_document(values: Mapping[str, str]) -> TOMLDocument:
    document = tomlkit.parse(_TEMPLATE.read_text(encoding="utf-8"))
    for key, value in values.items():
        if key in {"MEMU_CLIENT_ID", "MEMU_LLM_PROVIDER"}:
            continue
        if key in KEYS:
            _set(document, KEYS[key], typed_value(key, value))
        else:
            # Preserve custom / future keys as data, never interpolate them as TOML paths.
            if "legacy" not in document:
                document["legacy"] = tomlkit.table()
            document["legacy"][key] = value
    # An explicitly empty modern key must not erase a usable legacy alias,
    # regardless of the assignment order in the old file.
    if not values.get("MEMU_EMBED_PROVIDER") and values.get("MEMU_LLM_PROVIDER"):
        _set(document, KEYS["MEMU_EMBED_PROVIDER"], values["MEMU_LLM_PROVIDER"])
    _flatten(document)
    return document


def _state_values() -> dict[str, str]:
    try:
        document = _load(state_path())
    except FileNotFoundError:
        return {}
    value = document.get("client_id")
    if value is not None and not isinstance(value, str):
        raise ValueError("client_id must be a string")  # noqa: TRY003
    return {"MEMU_CLIENT_ID": value} if value else {}


def _write_state(value: str) -> None:
    try:
        document = _load(state_path())
    except FileNotFoundError:
        document = tomlkit.document()
    document["client_id"] = value
    _atomic_write(state_path(), tomlkit.dumps(document))


def _migrate() -> bool:
    target = config_path()
    if target.exists() or not legacy_path().is_file():
        return False
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with FileLock(str(target) + ".lock", timeout=10):
        if target.exists():
            return False
        values = _legacy_read()
        document = _new_document(values)
        if (value := values.get("MEMU_CLIENT_ID")) and not _state_values():
            _write_state(value)
        # The source remains byte-for-byte intact as the rollback copy.
        _atomic_write(target, tomlkit.dumps(document))
        print(f"memU: migrated {legacy_path()} to {target}; original file retained", file=sys.stderr)
        unknown = set(values) - KEYS.keys() - {"MEMU_CLIENT_ID", "MEMU_LLM_PROVIDER"}
        if unknown:
            print("memU: preserved compatibility keys in [legacy]: " + ", ".join(sorted(unknown)), file=sys.stderr)
        return True


def read() -> dict[str, str]:
    """Read disk only. Failed automatic migration leaves legacy configuration usable."""
    try:
        _migrate()
    except (OSError, ValueError, tomlkit.exceptions.TOMLKitError) as exc:
        # Exception text may include a credential-bearing source line.
        print(f"memU: configuration migration failed ({type(exc).__name__}); using legacy file", file=sys.stderr)
        return _legacy_read()
    try:
        values = _flatten(_load(config_path()))
    except FileNotFoundError:
        values = _legacy_read()
    return {**values, **_state_values()}


def write_values(updates: Mapping[str, str], *, comments: str = "") -> tuple[Path, bool]:
    """Merge under a lock; preserve TOML comments, unknown tables and identity."""
    # Keep the existing signature for command callers; TOML ships its own template.
    del comments
    migrated = _migrate()
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with FileLock(str(path) + ".lock", timeout=10):
        try:
            document = _load(path)
        except FileNotFoundError:
            document = _new_document({})
        for key, value in updates.items():
            if key == "MEMU_CLIENT_ID":
                _write_state(value)
            elif key in KEYS:
                _set(document, KEYS[key], typed_value(key, value))
            else:
                if "legacy" not in document:
                    document["legacy"] = tomlkit.table()
                document["legacy"][key] = value
        _flatten(document)
        changed = _atomic_write(path, tomlkit.dumps(document))
    return path, changed or migrated


def _atomic_write(path: Path, text: str) -> bool:
    if path.is_file() and path.read_bytes() == text.encode("utf-8"):
        _restrict(path)
        return False
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        _restrict(tmp)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise
    return True


def permission_note() -> str:
    return "chmod 600" if os.name == "posix" else "plaintext key; Windows ACLs inherited"


def _split(raw: str) -> tuple[str, str]:
    line = raw.strip()
    if not line or line.startswith("#"):
        return "", ""
    key, sep, value = line.partition("=")
    return (key.strip(), value) if sep else ("", "")


def _restrict(path: Path) -> None:
    if os.name != "posix":
        return
    with contextlib.suppress(OSError):
        path.chmod(0o600)
