from __future__ import annotations

import argparse
import json
import pathlib
from collections.abc import Callable, Iterator
from typing import Any

import httpx
import pytest

from memu import env as menv
from memu.cloud import (
    DEFAULT_CLOUD_BASE_URL,
    CloudAuthenticationError,
    CloudAuthorizationError,
    CloudMemoryClient,
    CloudRateLimitError,
    CloudServiceError,
    CloudTransportError,
    CloudValidationError,
)
from memu.hosts import retrieval
from memu.hosts.codex.cli import SPEC
from memu.hosts.host_cli import _cmd_doctor

Handler = Callable[[httpx.Request], httpx.Response]


def _client(handler: Handler, *, max_attempts: int = 3) -> CloudMemoryClient:
    return CloudMemoryClient(
        base_url="https://cloud.example/api/v4/memory/",
        api_key="project-key",
        max_attempts=max_attempts,
        transport=httpx.MockTransport(handler),
    )


async def test_list_uses_v4_base_auth_and_explicit_default_scope() -> None:
    seen: list[httpx.Request] = []
    payload = {"categories": [{"name": "profile"}]}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=payload)

    result = await _client(handler).list_all_recall_files()

    assert result == payload
    assert len(seen) == 1
    request = seen[0]
    assert request.method == "GET"
    assert request.url.path == "/api/v4/memory"
    assert dict(request.url.params) == {"user_id": "default", "agent_id": "default"}
    assert request.headers["Authorization"] == "Bearer project-key"


async def test_search_maps_scope_and_passes_response_through() -> None:
    response_payload = {
        "segments": [{"id": "s1", "score": 0.9}],
        "files": [{"id": "f1", "score": 0.9}],
        "resources": [],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v4/memory/search"
        assert json.loads(request.content) == {
            "query": "tea",
            "user_id": "u1",
            "agent_id": "a1",
        }
        return httpx.Response(200, json=response_payload)

    result = await _client(handler).progressive_retrieve("tea", where={"user_id": "u1", "agent_id": "a1"})
    assert result == response_payload


async def test_base_operation_uses_slashless_collection_route() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(200, json={"categories": []})

    assert await _client(handler).list_all_recall_files() == {"categories": []}
    assert paths == ["/api/v4/memory"]


async def test_commit_sends_recall_files_resources_and_default_user() -> None:
    recall_files = [{"name": "profile", "track": "memory", "content": "likes tea"}]
    resources = [{"path": "/workspace/notes.md", "description": "launch notes"}]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v4/memory"
        assert json.loads(request.content) == {
            "user": {"user_id": "default", "agent_id": "default"},
            "recall_files": recall_files,
            "resource": resources,
        }
        return httpx.Response(200, json={"recall_files": recall_files, "resources": []})

    result = await _client(handler).commit_results(recall_files=recall_files, resource=resources)
    assert result == {"recall_files": recall_files, "resources": []}


async def test_commit_maps_named_user_scope() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["user"] == {
            "user_id": "u1",
            "agent_id": "a1",
            "user_name": "User",
            "agent_name": "Agent",
        }
        return httpx.Response(200, json={"recall_files": [], "resources": []})

    await _client(handler).commit_results(
        user={"user_id": "u1", "agent_id": "a1", "user_name": "User", "agent_name": "Agent"}
    )


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (401, CloudAuthenticationError),
        (403, CloudAuthorizationError),
        (422, CloudValidationError),
        (429, CloudRateLimitError),
        (500, CloudServiceError),
    ],
)
async def test_structured_errors_are_typed_and_include_service_message(
    status: int,
    error_type: type[Exception],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status,
            json={"message": "useful service message", "details": [{"code": "MEMORY_ERROR"}]},
        )

    with pytest.raises(error_type, match=r"useful service message.*MEMORY_ERROR"):
        await _client(handler, max_attempts=1).list_all_recall_files()


async def test_transient_status_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    async def no_sleep(delay: float) -> None:
        assert delay >= 0

    monkeypatch.setattr("memu.cloud.asyncio.sleep", no_sleep)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, json={"message": "try again"})
        return httpx.Response(200, json={"categories": []})

    assert await _client(handler).list_all_recall_files() == {"categories": []}
    assert calls == 2


async def test_authentication_error_is_not_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(401, json={"message": "bad key"})

    with pytest.raises(CloudAuthenticationError):
        await _client(handler).list_all_recall_files()
    assert calls == 1


async def test_transport_failure_is_retried_then_classified(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    async def no_sleep(delay: float) -> None:
        assert delay >= 0

    monkeypatch.setattr("memu.cloud.asyncio.sleep", no_sleep)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("offline", request=request)

    with pytest.raises(CloudTransportError, match="offline"):
        await _client(handler, max_attempts=2).list_all_recall_files()
    assert calls == 2


async def test_cloud_rejects_unsupported_scope_filters() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        pytest.fail("request should not be sent")

    with pytest.raises(ValueError, match="user_id__in"):
        await _client(handler).progressive_retrieve("query", where={"user_id__in": ["u1"]})


async def test_invalid_success_response_is_not_silently_accepted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["unexpected"])

    with pytest.raises(CloudServiceError, match="unexpected response shape"):
        await _client(handler).list_all_recall_files()


@pytest.fixture()
def config_file(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> Iterator[pathlib.Path]:
    for key in (
        "MEMU_MEMORY_MODE",
        "MEMU_CLOUD_BASE_URL",
        "MEMU_CLOUD_API_KEY",
        "MEMU_DB",
        "MEMU_EMBED_PROVIDER",
    ):
        monkeypatch.delenv(key, raising=False)
    path = tmp_path / "config.env"
    monkeypatch.setenv("MEMU_CONFIG_ENV", str(path))
    menv.reload()
    yield path
    menv.reload()


def test_unset_mode_defaults_to_local(config_file: pathlib.Path) -> None:
    backend = menv.build_agentic_memory_backend_from_env(
        local_database=":memory:",
        local_embedding_profile={"provider": "openai"},
    )
    from memu.app import MemoryService

    assert menv.memory_mode() == "local"
    assert isinstance(backend, MemoryService)


def test_cloud_factory_needs_no_local_configuration(config_file: pathlib.Path) -> None:
    config_file.write_text(
        "MEMU_MEMORY_MODE=cloud\nMEMU_CLOUD_API_KEY=secret\n",
        encoding="utf-8",
    )
    menv.reload()

    backend = menv.build_agentic_memory_backend_from_env()

    assert isinstance(backend, CloudMemoryClient)
    assert backend.base_url == DEFAULT_CLOUD_BASE_URL
    assert backend.api_key == "secret"


def test_cloud_factory_accepts_staging_override(config_file: pathlib.Path) -> None:
    staging = "https://staging-api.memu.so/api/v4/memory/"
    config_file.write_text(
        f"MEMU_MEMORY_MODE=cloud\nMEMU_CLOUD_BASE_URL={staging}\nMEMU_CLOUD_API_KEY=secret\n",
        encoding="utf-8",
    )
    menv.reload()

    backend = menv.build_agentic_memory_backend_from_env()

    assert isinstance(backend, CloudMemoryClient)
    assert backend.base_url == staging


def test_cloud_factory_requires_cloud_key(config_file: pathlib.Path) -> None:
    config_file.write_text("MEMU_MEMORY_MODE=cloud\n", encoding="utf-8")
    menv.reload()

    with pytest.raises(menv.ConfigError, match=r"MEMU_CLOUD_API_KEY.*required in cloud mode"):
        menv.build_agentic_memory_backend_from_env()


def test_cloud_factory_does_not_create_local_database_path(
    config_file: pathlib.Path,
    tmp_path: pathlib.Path,
) -> None:
    config_file.write_text("MEMU_MEMORY_MODE=cloud\nMEMU_CLOUD_API_KEY=secret\n", encoding="utf-8")
    menv.reload()
    local_db = tmp_path / "should-not-exist" / "memu.sqlite3"

    menv.build_agentic_memory_backend_from_env(local_database=str(local_db))

    assert not local_db.parent.exists()


def test_invalid_mode_is_a_clear_config_error(config_file: pathlib.Path) -> None:
    config_file.write_text("MEMU_MEMORY_MODE=remote\n", encoding="utf-8")
    menv.reload()

    with pytest.raises(menv.ConfigError, match=r"local.*cloud"):
        menv.memory_mode()


async def test_doctor_reports_cloud_mode_endpoint_and_resource_limitation(
    config_file: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_file.write_text(
        "MEMU_MEMORY_MODE=cloud\nMEMU_CLOUD_API_KEY=secret\n",
        encoding="utf-8",
    )
    menv.reload()

    async def retrieve_ok(query: str) -> dict[str, list[Any]]:
        assert query == "smoke test"
        return {"segments": [], "files": [], "resources": []}

    monkeypatch.setattr(retrieval, "retrieve", retrieve_ok)

    assert await _cmd_doctor(SPEC, argparse.Namespace()) == 0
    output = capsys.readouterr().out
    assert "mode      cloud" in output
    assert f"endpoint  {DEFAULT_CLOUD_BASE_URL}" in output
    assert "accepted but not currently persisted" in output
    assert "retrieval ok" in output


async def test_host_retrieval_uses_shared_backend_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    class Backend:
        async def progressive_retrieve(
            self,
            query: str,
            where: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            assert query == "tea"
            assert where == {"user_id": "u1"}
            return {"segments": [], "files": [], "resources": []}

    monkeypatch.setattr(retrieval, "build_agentic_memory_backend_from_env", lambda: Backend())

    assert await retrieval.retrieve("tea", where={"user_id": "u1"}) == {
        "segments": [],
        "files": [],
        "resources": [],
    }
