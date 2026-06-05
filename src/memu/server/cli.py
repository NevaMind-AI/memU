from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence

from memu._version import __version__
from memu.server.app import MAX_REQUEST_BYTES, normalize_api_key, run_server
from memu.server.config import build_memory_service_from_env
from memu.server.openapi import openapi_schema


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memu-server",
        description="Run the built-in memU self-hosted JSON API server.",
    )
    parser.add_argument("--host", default=os.getenv("MEMU_SERVER_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=_port_arg, default=os.getenv("MEMU_SERVER_PORT", "8765"))
    parser.add_argument(
        "--max-request-bytes",
        type=_positive_int_arg,
        default=os.getenv("MEMU_SERVER_MAX_REQUEST_BYTES", str(MAX_REQUEST_BYTES)),
        help="Maximum JSON request body size in bytes. Defaults to MEMU_SERVER_MAX_REQUEST_BYTES or 10 MiB.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Bearer token required for memory endpoints. Defaults to MEMU_SERVER_API_KEY when set.",
    )
    parser.add_argument(
        "--api-key-env",
        default="MEMU_SERVER_API_KEY",
        help="Environment variable used for the bearer token when --api-key is omitted.",
    )
    parser.add_argument(
        "--print-openapi",
        action="store_true",
        help="Print the built-in OpenAPI schema and exit without starting a server.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.print_openapi:
        print(json.dumps(openapi_schema(), indent=2, sort_keys=True))
        return 0

    api_key = normalize_api_key(args.api_key if args.api_key is not None else os.getenv(args.api_key_env))
    service = build_memory_service_from_env()
    print(f"memU server listening on http://{args.host}:{args.port}", flush=True)
    if api_key:
        print("auth: bearer token enabled", flush=True)
    else:
        print("auth: disabled; set MEMU_SERVER_API_KEY or pass --api-key to enable", flush=True)
    run_server(
        service,
        host=args.host,
        port=args.port,
        api_key=api_key,
        max_request_bytes=args.max_request_bytes,
    )
    return 0


def _port_arg(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if port <= 0 or port > 65535:
        raise argparse.ArgumentTypeError("must be between 1 and 65535")
    return port


def _positive_int_arg(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


if __name__ == "__main__":
    raise SystemExit(main())
