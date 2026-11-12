"""CLI entry point for memu-server."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence


def main(args: Sequence[str] | None = None) -> int:
    """Main entry point for memu-server CLI."""
    parser = argparse.ArgumentParser(
        prog="memu-server",
        description="MemU Server - AI Memory and Conversation Management Framework",
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.4.0",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start command
    start_parser = subparsers.add_parser(
        "start",
        help="Start the MemU server",
    )
    start_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    start_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )
    start_parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file",
    )
    
    # Info command
    info_parser = subparsers.add_parser(
        "info",
        help="Show system information",
    )
    
    parsed = parser.parse_args(args)
    
    if parsed.command == "start":
        print("🧠 Starting MemU server...")
        print(f"   Host: {parsed.host}")
        print(f"   Port: {parsed.port}")
        if parsed.config:
            print(f"   Config: {parsed.config}")
        print()
        print("⚠️  Note: Full server implementation is in development.")
        print("   Currently, use MemoryService programmatically:")
        print()
        print("   from memu import MemoryService")
        print("   service = MemoryService()")
        print()
        return 0
    
    elif parsed.command == "info":
        print("🧠 MemU - AI Memory Framework")
        print("   Version: 1.4.0")
        print("   Python: >=3.13")
        print()
        print("   For documentation, visit:")
        print("   https://github.com/NevaMind-AI/MemU")
        return 0
    
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
