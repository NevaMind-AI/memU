from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version


def _package_version() -> str:
    try:
        return version("memu-py")
    except PackageNotFoundError:
        return "unknown"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memu-server",
        description="Compatibility CLI for the memu Python package.",
    )
    parser.add_argument("--version", action="store_true", help="Show memu package version and exit.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.version:
        print(f"memu {_package_version()}")
        return 0

    print("`memu-server` in this package is a compatibility stub.")
    print("The full backend server lives in the separate repository:")
    print("https://github.com/NevaMind-AI/memU-server")
    print("Use the `memu` Python API in this package for local memory workflows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
