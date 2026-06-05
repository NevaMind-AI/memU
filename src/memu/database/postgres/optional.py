from __future__ import annotations

POSTGRES_EXTRA_INSTALL_HINT = (
    "Postgres storage requires the optional Postgres dependencies. "
    "Install them with `pip install 'memu-py[postgres]'`, or run "
    "`uv sync --extra postgres` from a source checkout."
)


def postgres_extra_import_error() -> ImportError:
    return ImportError(POSTGRES_EXTRA_INSTALL_HINT)


__all__ = ["POSTGRES_EXTRA_INSTALL_HINT", "postgres_extra_import_error"]
