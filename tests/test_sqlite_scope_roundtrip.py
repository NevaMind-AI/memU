"""Scope metadata survives the public API and SQLite's export/cache boundary."""

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


async def test_distinct_scope_services_share_a_process(tmp_path):
    # Independent applications use independent database files and schema models.
    # Both services must remain usable after creating a second schema model.
    scopes: list[tuple[type[BaseModel], dict[str, Any]]] = [
        (DefaultUserModel, {"user_id": "alice"}),
        (TenantScope, {"tenant_id": "bob", "shard": 7}),
    ]
    services: list[tuple[MemoryService, dict[str, Any], type[BaseModel], dict[str, Any]]] = []
    try:
        for index, (model, scope) in enumerate(scopes):
            config = {"metadata_store": {"provider": "sqlite", "dsn": f"sqlite:///{tmp_path}/{index}.db"}}
            services.append((make_service(config, model), config, model, scope))

        for service, _, _, scope in services:
            await service.commit_results(
                recall_files=[{"name": "preferences", "description": "coffee", "content": "likes coffee"}],
                resource=[{"path": "/workspace/notes.md", "description": "coffee notes"}],
                user=scope,
            )
        for service, config, model, scope in services:
            # Reopening also checks that cache reuse does not mix model types.
            service.database.close()
            reopened = make_service(config, model)
            try:
                listed = await reopened.list_all_recall_files(where=scope)
                retrieved = await reopened.progressive_retrieve("coffee", where=scope)
                assert len(listed["recall_files"]) == 1
                for records in (listed["recall_files"], *retrieved.values()):
                    assert records
                    for record in records:
                        assert {key: record.get(key) for key in scope} == scope
            finally:
                reopened.database.close()
    finally:
        for service, _, _, _ in services:
            service.database.close()
