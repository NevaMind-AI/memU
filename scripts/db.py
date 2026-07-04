#!/usr/bin/env python
"""Programmatic Alembic entry point for the Postgres backend.

The migration environment is parameterized by a user *scope model* (see
``memu.database.postgres.schema.get_metadata``). The bare ``alembic`` CLI cannot
pass that in, so this wrapper builds the config via
``memu.database.postgres.migration.make_alembic_config`` and drives Alembic's
command API directly.

The default scope model is ``None`` (the base schema with no scope columns),
which is the schema committed under ``migrations/versions``.

Usage:
    python scripts/db.py revision -m "add foo"     # autogenerate a revision
    python scripts/db.py upgrade [head]            # apply migrations
    python scripts/db.py downgrade -1              # revert one revision
    python scripts/db.py current                   # show applied revision
    python scripts/db.py history                   # show revision history

DSN resolution: --dsn, else $MEMU_DB_DSN, else a localhost default.
"""

from __future__ import annotations

import argparse
import os
import sys

from alembic import command

from memu.database.postgres.migration import make_alembic_config

DEFAULT_DSN = "postgresql+psycopg://postgres:postgres@localhost:5432/memu"


def _config(dsn: str):
    # scope_model=None -> base schema (matches committed baseline revision).
    return make_alembic_config(dsn=dsn, scope_model=None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MemU Postgres migrations")
    parser.add_argument(
        "--dsn",
        default=os.environ.get("MEMU_DB_DSN", DEFAULT_DSN),
        help="SQLAlchemy DSN (default: $MEMU_DB_DSN or localhost memu db)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_rev = sub.add_parser("revision", help="create a new revision")
    p_rev.add_argument("-m", "--message", required=True)
    p_rev.add_argument(
        "--no-autogenerate",
        action="store_true",
        help="create an empty revision instead of diffing against the DB",
    )

    p_up = sub.add_parser("upgrade", help="apply migrations")
    p_up.add_argument("revision", nargs="?", default="head")

    p_down = sub.add_parser("downgrade", help="revert migrations")
    p_down.add_argument("revision")

    sub.add_parser("current", help="show current revision")

    p_hist = sub.add_parser("history", help="show revision history")
    p_hist.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args(argv)
    cfg = _config(args.dsn)

    if args.cmd == "revision":
        command.revision(cfg, message=args.message, autogenerate=not args.no_autogenerate)
    elif args.cmd == "upgrade":
        command.upgrade(cfg, args.revision)
    elif args.cmd == "downgrade":
        command.downgrade(cfg, args.revision)
    elif args.cmd == "current":
        command.current(cfg, verbose=True)
    elif args.cmd == "history":
        command.history(cfg, verbose=args.verbose)
    else:  # pragma: no cover - argparse guards this
        parser.error(f"unknown command: {args.cmd}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
