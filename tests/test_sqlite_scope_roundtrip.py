"""Scope metadata survives the public API and SQLite's export/cache boundary."""

import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from memu.app import MemoryService
from memu.app.settings import DefaultUserModel


class TenantScope(BaseModel):
    tenant_id: str
    shard: int = 7


class Embedding:
    async def embed(self, texts: list[str]) -> tuple[list[list[float]], None]:
        return [[1.0, 0.5] for _ in texts], None


def make_service(config: dict[str, Any], scope_model: type[BaseModel]) -> MemoryService:
    result = MemoryService(database_config=config, user_config={"model": scope_model})
    result._embedding_pool._cache["embedding"] = Embedding()
    return result


@pytest.mark.parametrize("provider", ["inmemory", "sqlite"])
async def test_public_api_keeps_scope_on_returned_records(provider, tmp_path):
    await assert_scope_roundtrip(provider, DefaultUserModel, "user_id", {"agent_id": "assistant"}, tmp_path)


async def assert_scope_roundtrip(provider, scope_model, scope_key, extra_scope, tmp_path):
    config = {"metadata_store": {"provider": provider}}
    if provider == "sqlite":
        config["metadata_store"]["dsn"] = f"sqlite:///{tmp_path}/memory.db"
    app = make_service(config, scope_model)
    for owner in ("alice", "bob"):
        scope = {scope_key: owner, **extra_scope}
        # A second commit exercises update hydration as well as create hydration.
        for suffix in ("", " daily"):
            committed = await app.commit_results(
                recall_files=[
                    {
                        "name": "preferences",
                        "description": "coffee" + suffix,
                        "content": f"{owner} likes coffee{suffix}",
                    }
                ],
                resource=[{"path": f"/workspace/{owner}.md", "description": "coffee notes" + suffix}],
                user=scope,
            )
            for records in committed.values():
                for record in records:
                    assert {key: record.get(key) for key in scope} == scope
                    assert "embedding" not in record

    if provider == "sqlite":
        app._get_database().close()
        app = make_service(config, scope_model)
    listed = await app.list_all_recall_files(where={scope_key: "alice"})
    assert len(listed["recall_files"]) == 1
    assert listed["recall_files"][0]["content"] == "alice likes coffee daily"
    retrieved = await app.progressive_retrieve("coffee", where={scope_key: "alice"})
    scope = {scope_key: "alice", **extra_scope}
    for records in (listed["recall_files"], *retrieved.values()):
        assert records
        for record in records:
            assert {key: record.get(key) for key in scope} == scope
            assert "embedding" not in record
    assert not (await app.list_all_recall_files(where={scope_key: "missing"}))["recall_files"]


async def test_documented_sqlite_export_retains_resource_owner(tmp_path):
    config = {"metadata_store": {"provider": "sqlite", "dsn": f"sqlite:///{tmp_path}/memory.db"}}
    app = make_service(config, DefaultUserModel)
    await app.commit_results(
        resource=[{"path": "/workspace/notes.md", "description": "coffee"}], user={"user_id": "alice"}
    )
    app._get_database().close()
    reopened = make_service(config, DefaultUserModel)
    db = reopened._get_database()
    db.load_existing()
    # Exact consumer in docs/sqlite.md's SQLite-to-PostgreSQL export example.
    # No PostgreSQL connection is needed to verify the exported payload.
    payloads = [{"user_id": getattr(resource, "user_id", None)} for resource in db.resources.values()]
    assert payloads == [{"user_id": "alice"}]


def test_custom_scope_roundtrip_in_fresh_process(tmp_path):
    # SQLite's ORM schema factory currently shares Column instances between scope
    # classes. A separate process reflects a deployment choosing one scope model,
    # without changing that unrelated schema limitation in this regression.
    result = subprocess.run(  # noqa: S603 - executes only this checked-in test with a temporary directory.
        [sys.executable, str(Path(__file__).resolve()), str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


if __name__ == "__main__":
    asyncio.run(assert_scope_roundtrip("sqlite", TenantScope, "tenant_id", {"shard": 7}, Path(sys.argv[1])))
