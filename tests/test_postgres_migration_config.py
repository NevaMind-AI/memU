import importlib.util
from pathlib import Path

from pydantic import BaseModel


def _load_migration_module():
    module_path = Path(__file__).resolve().parents[1] / "src/memu/database/postgres/migration.py"
    spec = importlib.util.spec_from_file_location("memu_postgres_migration", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _ScopeModel(BaseModel):
    user_id: str


def test_make_alembic_config_escapes_percent_encoded_dsn() -> None:
    migration = _load_migration_module()

    dsn = "postgresql+psycopg://postgres:%40%23%24%25%5E%26%2A%28%29password@host.docker.internal:5432/memu_dev"

    cfg = migration.make_alembic_config(dsn=dsn, scope_model=_ScopeModel)
    raw_value = cfg.file_config.get(cfg.config_ini_section, "sqlalchemy.url", raw=True)

    assert cfg.get_main_option("sqlalchemy.url") == dsn
    assert "%%40%%23%%24%%25%%5E%%26%%2A%%28%%29password" in raw_value
    assert raw_value != dsn
