from __future__ import annotations

import contextlib
import http.client
import io
import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from pydantic import BaseModel

from memu._version import __version__
from memu.server.app import (
    DELETE_PATHS,
    MAX_REQUEST_BYTES,
    MemUServerConfig,
    POST_PATHS,
    POST_ROUTE_HANDLERS,
    PUBLIC_GET_PATHS,
    _allowed_methods_for_path,
    _json_default,
    _normalize_queries,
    _parse_content_length,
    create_handler,
)
from memu.server.cli import build_parser, main as server_cli_main
from memu.server.constants import SUPPORTED_MEMORIZE_MODALITIES, SUPPORTED_MEMORY_TYPES
from memu.server.openapi import openapi_schema


class ServerResponseRecord(BaseModel):
    id: str
    summary: str
    embedding: list[float] | None
    created_at: datetime


class FakeMemoryService:
    def __init__(self) -> None:
        self.database_config = SimpleNamespace(
            metadata_store=SimpleNamespace(provider="inmemory"),
            vector_index=SimpleNamespace(provider="bruteforce"),
        )
        self.memorize_calls: list[dict[str, Any]] = []
        self.retrieve_calls: list[dict[str, Any]] = []
        self.create_item_calls: list[dict[str, Any]] = []
        self.update_item_calls: list[dict[str, Any]] = []
        self.delete_item_calls: list[dict[str, Any]] = []

    def _provider_summary(self) -> dict[str, Any]:
        return {
            "llm_profiles": ["default", "embedding"],
            "storage": {
                "metadata_store": self.database_config.metadata_store.provider,
                "vector_index": self.database_config.vector_index.provider,
            },
        }

    async def memorize(
        self,
        *,
        resource_url: str,
        modality: str,
        user: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.memorize_calls.append({"resource_url": resource_url, "modality": modality, "user": user})
        return {"resource_url": resource_url, "modality": modality, "user": user}

    async def retrieve(
        self,
        queries: list[dict[str, Any]],
        where: dict[str, Any] | None = None,
        method: str | None = None,
        ranking: str | None = None,
    ) -> dict[str, Any]:
        self.retrieve_calls.append({"queries": queries, "where": where, "method": method, "ranking": ranking})
        return {"queries": queries, "where": where, "method": method, "ranking": ranking, "items": []}

    async def list_memory_categories(self, where: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"categories": [], "where": where}

    async def list_memory_items(self, where: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"items": [], "where": where}

    async def clear_memory(self, where: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"deleted": {}, "where": where}

    async def create_memory_item(
        self,
        *,
        memory_type: str,
        memory_content: str,
        memory_categories: list[str],
        user: dict[str, Any] | None = None,
        propagate: bool = True,
    ) -> dict[str, Any]:
        call = {
            "memory_type": memory_type,
            "memory_content": memory_content,
            "memory_categories": memory_categories,
            "user": user,
            "propagate": propagate,
        }
        self.create_item_calls.append(call)
        return {"memory_item": {"id": "m1", **call}}

    async def update_memory_item(
        self,
        *,
        memory_id: str,
        memory_type: str | None = None,
        memory_content: str | None = None,
        memory_categories: list[str] | None = None,
        user: dict[str, Any] | None = None,
        propagate: bool = True,
    ) -> dict[str, Any]:
        call = {
            "memory_id": memory_id,
            "memory_type": memory_type,
            "memory_content": memory_content,
            "memory_categories": memory_categories,
            "user": user,
            "propagate": propagate,
        }
        self.update_item_calls.append(call)
        return {"memory_item": {"id": memory_id, **call}}

    async def delete_memory_item(
        self,
        *,
        memory_id: str,
        user: dict[str, Any] | None = None,
        propagate: bool = True,
    ) -> dict[str, Any]:
        call = {"memory_id": memory_id, "user": user, "propagate": propagate}
        self.delete_item_calls.append(call)
        return {"memory_item": {"id": memory_id}, **call}


@contextmanager
def running_server(
    service: FakeMemoryService,
    *,
    api_key: str | None = None,
    max_request_bytes: int | None = None,
) -> Iterator[tuple[str, int]]:
    config = MemUServerConfig(
        api_key=api_key,
        max_request_bytes=max_request_bytes or MemUServerConfig.max_request_bytes,
    )
    handler = create_handler(service, config=config)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield str(host), int(port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def request_json(
    host: str,
    port: int,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    body = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
    request_headers = {"Content-Type": "application/json"}
    request_headers.update(headers or {})
    conn = http.client.HTTPConnection(host, port, timeout=5)
    try:
        conn.request(method, path, body=body, headers=request_headers)
        response = conn.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        return response.status, data
    finally:
        conn.close()


def request_json_with_headers(
    host: str,
    port: int,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any], dict[str, str]]:
    body = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
    request_headers = {"Content-Type": "application/json"}
    request_headers.update(headers or {})
    conn = http.client.HTTPConnection(host, port, timeout=5)
    try:
        conn.request(method, path, body=body, headers=request_headers)
        response = conn.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        return response.status, data, dict(response.getheaders())
    finally:
        conn.close()


def request_bytes_with_headers(
    host: str,
    port: int,
    method: str,
    path: str,
    payload: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, bytes, dict[str, str]]:
    request_headers = {"Content-Type": "application/json"}
    request_headers.update(headers or {})
    conn = http.client.HTTPConnection(host, port, timeout=5)
    try:
        conn.request(method, path, body=payload, headers=request_headers)
        response = conn.getresponse()
        return response.status, response.read(), dict(response.getheaders())
    finally:
        conn.close()


def request_raw(
    host: str,
    port: int,
    method: str,
    path: str,
    body: bytes,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    request_headers = {"Content-Type": "application/json", "Content-Length": str(len(body))}
    request_headers.update(headers or {})
    conn = http.client.HTTPConnection(host, port, timeout=5)
    try:
        conn.request(method, path, body=body, headers=request_headers)
        response = conn.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        return response.status, data
    finally:
        conn.close()


def test_server_json_default_uses_public_json_safe_model_dump() -> None:
    record = ServerResponseRecord(
        id="m1",
        summary="User likes concise answers.",
        embedding=[0.1, 0.2],
        created_at=datetime(2026, 6, 5, 1, 40, tzinfo=timezone.utc),
    )

    data = json.loads(json.dumps({"record": record}, default=_json_default))

    assert data == {
        "record": {
            "id": "m1",
            "summary": "User likes concise answers.",
            "created_at": "2026-06-05T01:40:00Z",
        }
    }


def test_server_config_rejects_non_positive_max_request_bytes() -> None:
    try:
        MemUServerConfig(max_request_bytes=0)
    except ValueError as exc:
        assert "max_request_bytes must be positive" in str(exc)
    else:
        raise AssertionError("max_request_bytes must be positive")


def test_server_cli_parser_exists() -> None:
    parser = build_parser()
    args = parser.parse_args(["--host", "0.0.0.0", "--port", "9999"])
    assert args.host == "0.0.0.0"
    assert args.port == 9999
    assert args.max_request_bytes == MAX_REQUEST_BYTES


@patch.dict("os.environ", {"MEMU_SERVER_PORT": "9998"})
def test_server_cli_parser_uses_port_env_default() -> None:
    parser = build_parser()
    args = parser.parse_args([])

    assert args.port == 9998


@patch.dict("os.environ", {"MEMU_SERVER_MAX_REQUEST_BYTES": "2048"})
def test_server_cli_parser_uses_max_request_bytes_env_default() -> None:
    parser = build_parser()
    args = parser.parse_args([])

    assert args.max_request_bytes == 2048


@patch.dict("os.environ", {"MEMU_SERVER_PORT": "abc"})
def test_server_cli_reports_invalid_port_env() -> None:
    stderr = io.StringIO()

    with contextlib.redirect_stderr(stderr):
        try:
            server_cli_main(["--print-openapi"])
        except SystemExit as exc:
            assert exc.code == 2
        else:
            raise AssertionError("invalid MEMU_SERVER_PORT should exit with argparse error")

    assert "argument --port: must be an integer" in stderr.getvalue()


@patch.dict("os.environ", {"MEMU_SERVER_MAX_REQUEST_BYTES": "abc"})
def test_server_cli_reports_invalid_max_request_bytes_env() -> None:
    stderr = io.StringIO()

    with contextlib.redirect_stderr(stderr):
        try:
            server_cli_main(["--print-openapi"])
        except SystemExit as exc:
            assert exc.code == 2
        else:
            raise AssertionError("invalid MEMU_SERVER_MAX_REQUEST_BYTES should exit with argparse error")

    assert "argument --max-request-bytes: must be an integer" in stderr.getvalue()


def test_server_cli_rejects_out_of_range_port() -> None:
    parser = build_parser()
    stderr = io.StringIO()

    with contextlib.redirect_stderr(stderr):
        try:
            parser.parse_args(["--port", "70000"])
        except SystemExit as exc:
            assert exc.code == 2
        else:
            raise AssertionError("--port outside 1..65535 should be rejected")

    assert "argument --port: must be between 1 and 65535" in stderr.getvalue()


def test_server_cli_rejects_non_positive_max_request_bytes() -> None:
    parser = build_parser()
    stderr = io.StringIO()

    with contextlib.redirect_stderr(stderr):
        try:
            parser.parse_args(["--max-request-bytes", "0"])
        except SystemExit as exc:
            assert exc.code == 2
        else:
            raise AssertionError("--max-request-bytes should be positive")

    assert "argument --max-request-bytes: must be a positive integer" in stderr.getvalue()


@patch.dict("os.environ", {"MEMU_SERVER_API_KEY": " secret "})
def test_server_cli_trims_api_key_env_before_running() -> None:
    service = FakeMemoryService()

    with (
        patch("memu.server.cli.build_memory_service_from_env", return_value=service),
        patch("memu.server.cli.run_server") as run_server_mock,
    ):
        exit_code = server_cli_main(["--host", "127.0.0.1", "--port", "9999"])

    assert exit_code == 0
    run_server_mock.assert_called_once_with(
        service,
        host="127.0.0.1",
        port=9999,
        api_key="secret",
        max_request_bytes=MAX_REQUEST_BYTES,
    )


def test_server_cli_passes_max_request_bytes_to_run_server() -> None:
    service = FakeMemoryService()

    with (
        patch("memu.server.cli.build_memory_service_from_env", return_value=service),
        patch("memu.server.cli.run_server") as run_server_mock,
    ):
        exit_code = server_cli_main(["--max-request-bytes", "4096"])

    assert exit_code == 0
    run_server_mock.assert_called_once_with(
        service,
        host="127.0.0.1",
        port=8765,
        api_key=None,
        max_request_bytes=4096,
    )


def test_server_health_endpoint_is_public() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret", max_request_bytes=2048) as (host, port):
        status, data, headers = request_json_with_headers(host, port, "GET", "/health")
        versioned_status, versioned_data = request_json(host, port, "GET", "/api/v3/health")

    assert status == 200
    assert data["ok"] is True
    assert data["version"] == __version__
    assert data["storage"] == "inmemory"
    assert data["providers"] == {
        "llm_profiles": ["default", "embedding"],
        "storage": {
            "metadata_store": "inmemory",
            "vector_index": "bruteforce",
        },
    }
    assert data["auth"] == {"enabled": True}
    assert data["limits"] == {"max_request_bytes": 2048}
    assert headers["Access-Control-Allow-Methods"] == "GET,HEAD,OPTIONS"
    assert versioned_status == 200
    assert versioned_data["ok"] is True
    assert versioned_data["storage"] == "inmemory"
    assert versioned_data["providers"]["storage"]["vector_index"] == "bruteforce"


def test_server_head_health_endpoint_is_public_and_bodyless() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret", max_request_bytes=2048) as (host, port):
        status, body, headers = request_bytes_with_headers(host, port, "HEAD", "/health")
        openapi_status, openapi_body, openapi_headers = request_bytes_with_headers(host, port, "HEAD", "/openapi.json")
        versioned_status, versioned_body, versioned_headers = request_bytes_with_headers(
            host,
            port,
            "HEAD",
            "/api/v3/health",
        )

    assert status == 200
    assert body == b""
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    assert headers["Access-Control-Allow-Methods"] == "GET,HEAD,OPTIONS"
    assert int(headers["Content-Length"]) > 0
    assert openapi_status == 200
    assert openapi_body == b""
    assert openapi_headers["Content-Type"] == "application/json; charset=utf-8"
    assert int(openapi_headers["Content-Length"]) > 0
    assert versioned_status == 200
    assert versioned_body == b""
    assert int(versioned_headers["Content-Length"]) > 0


def test_server_head_unknown_route_is_bodyless_not_found() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, body, headers = request_bytes_with_headers(host, port, "HEAD", "/api/v3/memory/missing")

    assert status == 404
    assert body == b""
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    assert int(headers["Content-Length"]) > 0


def test_server_openapi_endpoint_is_public() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_json(host, port, "GET", "/openapi.json")

    assert status == 200
    assert data["openapi"] == "3.1.0"
    assert data["info"]["version"] == __version__
    assert "/api/v3/health" in data["paths"]
    assert "/api/v3/openapi.json" in data["paths"]
    assert "/api/v3/memory/retrieve" in data["paths"]
    assert "/api/v3/memory/items/create" in data["paths"]
    assert "/api/v3/memory/items/update" in data["paths"]
    assert "/api/v3/memory/items/delete" in data["paths"]
    health_schema = data["components"]["schemas"]["HealthResponse"]
    modality_schema = data["components"]["schemas"]["Modality"]
    memory_type_schema = data["components"]["schemas"]["MemoryType"]
    assert health_schema["required"] == ["ok", "service", "version", "storage", "providers", "auth", "limits"]
    assert health_schema["properties"]["limits"]["properties"]["max_request_bytes"]["minimum"] == 1
    assert modality_schema["enum"] == list(SUPPORTED_MEMORIZE_MODALITIES)
    assert memory_type_schema["enum"] == list(SUPPORTED_MEMORY_TYPES)
    health_ref = data["paths"]["/health"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    versioned_health_ref = data["paths"]["/api/v3/health"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert health_ref == {"$ref": "#/components/schemas/HealthResponse"}
    assert versioned_health_ref == {"$ref": "#/components/schemas/HealthResponse"}
    assert data["paths"]["/health"]["head"]["responses"]["200"]["description"] == "Server health headers"
    assert data["paths"]["/openapi.json"]["head"]["responses"]["200"]["description"] == "OpenAPI contract headers"
    retrieve_post = data["paths"]["/api/v3/memory/retrieve"]["post"]
    retrieve_schema = retrieve_post["requestBody"]["content"]["application/json"]["schema"]
    assert {"required": ["query"]} in retrieve_schema["anyOf"]
    assert {"required": ["queries"]} in retrieve_schema["anyOf"]
    assert retrieve_schema["properties"]["queries"]["minItems"] == 1
    assert retrieve_schema["properties"]["method"]["enum"] == ["rag", "llm"]
    assert retrieve_schema["properties"]["ranking"]["enum"] == ["similarity", "salience"]
    create_schema = data["paths"]["/api/v3/memory/items/create"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert create_schema["required"] == ["memory_type", "memory_content", "memory_categories"]
    assert "405" in retrieve_post["responses"]


def test_server_openapi_paths_match_runtime_route_methods() -> None:
    schema = openapi_schema()
    expected_paths = PUBLIC_GET_PATHS | POST_PATHS | DELETE_PATHS

    assert set(schema["paths"]) == expected_paths
    for path in sorted(expected_paths):
        documented_methods = {method.upper() for method in schema["paths"][path]}
        runtime_methods = set(_allowed_methods_for_path(path)) - {"OPTIONS"}
        assert documented_methods == runtime_methods, path


def test_server_post_route_handlers_match_declared_post_paths() -> None:
    handler_class = create_handler(FakeMemoryService())

    assert set(POST_ROUTE_HANDLERS) == POST_PATHS
    for path, handler_name in POST_ROUTE_HANDLERS.items():
        assert handler_name.startswith("_"), path
        assert callable(getattr(handler_class, handler_name, None)), path


def test_server_options_reports_allowed_methods_for_known_routes() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        retrieve_status, retrieve_data, retrieve_headers = request_json_with_headers(
            host,
            port,
            "OPTIONS",
            "/api/v3/memory/retrieve",
        )
        health_status, health_data, health_headers = request_json_with_headers(host, port, "OPTIONS", "/health")
        delete_status, delete_data, delete_headers = request_json_with_headers(
            host,
            port,
            "OPTIONS",
            "/api/v3/memory",
        )

    assert retrieve_status == 200
    assert retrieve_data == {"ok": True}
    assert retrieve_headers["Allow"] == "POST,OPTIONS"
    assert retrieve_headers["Access-Control-Allow-Methods"] == "POST,OPTIONS"
    assert health_status == 200
    assert health_data == {"ok": True}
    assert health_headers["Allow"] == "GET,HEAD,OPTIONS"
    assert health_headers["Access-Control-Allow-Methods"] == "GET,HEAD,OPTIONS"
    assert delete_status == 200
    assert delete_data == {"ok": True}
    assert delete_headers["Allow"] == "DELETE,OPTIONS"


def test_server_options_rejects_unknown_routes() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_json(host, port, "OPTIONS", "/api/v3/memory/missing")

    assert status == 404
    assert data["error"]["code"] == "not_found"


def test_server_memorize_rejects_unknown_modality() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_json(
            host,
            port,
            "POST",
            "/api/v3/memory/memorize",
            {"resource_url": "memory.txt", "modality": "pdf"},
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 400
    assert data["error"]["code"] == "bad_request"
    assert "'modality' must be one of: conversation, document, image, audio, video" in data["error"]["message"]
    assert service.memorize_calls == []


def test_server_versioned_openapi_endpoint_is_public() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_json(host, port, "GET", "/api/v3/openapi.json")

    assert status == 200
    assert data["openapi"] == "3.1.0"
    assert data["info"]["version"] == __version__
    assert "/api/v3/openapi.json" in data["paths"]


def test_server_cli_prints_openapi(capsys: Any) -> None:
    exit_code = server_cli_main(["--print-openapi"])
    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert exit_code == 0
    assert data["info"]["title"] == "memU Self-Hosted API"
    assert data["info"]["version"] == __version__


def test_server_cli_prints_version_without_starting_server() -> None:
    stdout = io.StringIO()
    with (
        contextlib.redirect_stdout(stdout),
        patch("memu.server.cli.build_memory_service_from_env") as build_service_mock,
    ):
        try:
            server_cli_main(["--version"])
        except SystemExit as exc:
            assert exc.code == 0
        else:
            raise AssertionError("--version should exit through argparse")

    assert stdout.getvalue().strip() == f"memu-server {__version__}"
    build_service_mock.assert_not_called()


def test_server_rejects_missing_bearer_token() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_json(host, port, "POST", "/api/v3/memory/retrieve", {"query": "hello"})

    assert status == 401
    assert data["error"]["code"] == "unauthorized"


def test_server_trims_configured_bearer_token() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key=" secret ") as (host, port):
        status, data = request_json(
            host,
            port,
            "POST",
            "/api/v3/memory/retrieve",
            {"query": "hello"},
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 200
    assert data["items"] == []


def test_server_blank_api_key_disables_auth() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="   ") as (host, port):
        status, data = request_json(host, port, "POST", "/api/v3/memory/retrieve", {"query": "hello"})

    assert status == 200
    assert data["items"] == []


def test_server_rejects_unsupported_methods_with_json() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        put_status, put_data, put_headers = request_json_with_headers(
            host,
            port,
            "PUT",
            "/api/v3/memory/retrieve",
            {"query": "hello"},
            headers={"Authorization": "Bearer secret"},
        )
        patch_status, patch_data, patch_headers = request_json_with_headers(
            host,
            port,
            "PATCH",
            "/api/v3/memory/retrieve",
            {"query": "hello"},
            headers={"Authorization": "Bearer secret"},
        )

    assert put_status == 405
    assert put_data["error"]["code"] == "method_not_allowed"
    assert put_headers["Allow"] == "POST,OPTIONS"
    assert put_headers["Access-Control-Allow-Methods"] == "POST,OPTIONS"
    assert patch_status == 405
    assert patch_data["error"]["code"] == "method_not_allowed"
    assert patch_headers["Allow"] == "POST,OPTIONS"
    assert patch_headers["Access-Control-Allow-Methods"] == "POST,OPTIONS"


def test_server_rejects_wrong_methods_on_known_routes_with_precise_allow() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        get_status, get_data, get_headers = request_json_with_headers(
            host,
            port,
            "GET",
            "/api/v3/memory/retrieve",
        )
        head_status, head_body, head_headers = request_bytes_with_headers(
            host,
            port,
            "HEAD",
            "/api/v3/memory/retrieve",
        )
        post_status, post_data, post_headers = request_json_with_headers(
            host,
            port,
            "POST",
            "/health",
            {"query": "hello"},
        )
        delete_status, delete_data, delete_headers = request_json_with_headers(
            host,
            port,
            "DELETE",
            "/api/v3/memory/retrieve",
            {"query": "hello"},
        )

    assert get_status == 405
    assert get_data["error"]["code"] == "method_not_allowed"
    assert get_headers["Allow"] == "POST,OPTIONS"
    assert head_status == 405
    assert head_body == b""
    assert head_headers["Allow"] == "POST,OPTIONS"
    assert post_status == 405
    assert post_data["error"]["code"] == "method_not_allowed"
    assert post_headers["Allow"] == "GET,HEAD,OPTIONS"
    assert delete_status == 405
    assert delete_data["error"]["code"] == "method_not_allowed"
    assert delete_headers["Allow"] == "POST,OPTIONS"


def test_server_rejects_unsupported_methods_on_unknown_routes_as_not_found() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        put_status, put_data = request_json(
            host,
            port,
            "PUT",
            "/api/v3/memory/missing",
            {"query": "hello"},
            headers={"Authorization": "Bearer secret"},
        )
        patch_status, patch_data = request_json(
            host,
            port,
            "PATCH",
            "/api/v3/memory/missing",
            {"query": "hello"},
            headers={"Authorization": "Bearer secret"},
        )

    assert put_status == 404
    assert put_data["error"]["code"] == "not_found"
    assert patch_status == 404
    assert patch_data["error"]["code"] == "not_found"


def test_server_rejects_malformed_json_body() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_raw(
            host,
            port,
            "POST",
            "/api/v3/memory/retrieve",
            b'{"query"',
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 400
    assert data["error"]["code"] == "invalid_json"


def test_server_rejects_json_array_body() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_raw(
            host,
            port,
            "POST",
            "/api/v3/memory/retrieve",
            b'["not", "an", "object"]',
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 400
    assert data["error"]["code"] == "invalid_json"


def test_server_rejects_oversized_json_body() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret", max_request_bytes=8) as (host, port):
        status, data = request_raw(
            host,
            port,
            "POST",
            "/api/v3/memory/retrieve",
            b'{"query":"too large"}',
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 413
    assert data["error"]["code"] == "request_too_large"


def test_parse_content_length_rejects_invalid_values() -> None:
    assert _parse_content_length(None) == 0
    assert _parse_content_length("") == 0
    assert _parse_content_length("12") == 12
    assert _parse_content_length("-1") is None
    assert _parse_content_length("abc") is None


def test_normalize_queries_accepts_string_items() -> None:
    assert _normalize_queries({"queries": ["first", "second"]}) == [
        {"role": "user", "content": "first"},
        {"role": "user", "content": "second"},
    ]


def test_normalize_queries_accepts_structured_content() -> None:
    assert _normalize_queries({"queries": [{"role": "assistant", "content": {"text": " context "}}]}) == [
        {"role": "assistant", "content": {"text": "context"}},
    ]


def test_server_retrieve_accepts_query_shorthand() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data, headers = request_json_with_headers(
            host,
            port,
            "POST",
            "/api/v3/memory/retrieve",
            {"query": "what should I remember?", "where": {"user_id": "u1"}},
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 200
    assert data["items"] == []
    assert headers["Access-Control-Allow-Methods"] == "POST,OPTIONS"
    assert service.retrieve_calls == [
        {
            "queries": [{"role": "user", "content": "what should I remember?"}],
            "where": {"user_id": "u1"},
            "method": None,
            "ranking": None,
        }
    ]


def test_server_retrieve_rejects_missing_query() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_json(
            host,
            port,
            "POST",
            "/api/v3/memory/retrieve",
            {"where": {"user_id": "u1"}},
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 400
    assert data["error"]["code"] == "bad_request"


def test_server_retrieve_rejects_invalid_where_object() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_json(
            host,
            port,
            "POST",
            "/api/v3/memory/retrieve",
            {"query": "hello", "where": "u1"},
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 400
    assert data["error"]["code"] == "bad_request"
    assert "'where' must be an object" in data["error"]["message"]


def test_server_retrieve_accepts_string_query_items() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_json(
            host,
            port,
            "POST",
            "/api/v3/memory/retrieve",
            {"queries": ["previous context", "what should I remember?"]},
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 200
    assert data["items"] == []
    assert service.retrieve_calls == [
        {
            "queries": [
                {"role": "user", "content": "previous context"},
                {"role": "user", "content": "what should I remember?"},
            ],
            "where": {},
            "method": None,
            "ranking": None,
        }
    ]


def test_server_retrieve_accepts_method_override() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_json(
            host,
            port,
            "POST",
            "/api/v3/memory/retrieve",
            {"query": "what should I remember?", "method": " LLM "},
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 200
    assert data["method"] == "llm"
    assert service.retrieve_calls == [
        {
            "queries": [{"role": "user", "content": "what should I remember?"}],
            "where": {},
            "method": "llm",
            "ranking": None,
        }
    ]


def test_server_retrieve_accepts_ranking_override() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_json(
            host,
            port,
            "POST",
            "/api/v3/memory/retrieve",
            {"query": "what should I remember?", "ranking": " SALIENCE "},
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 200
    assert data["ranking"] == "salience"
    assert service.retrieve_calls == [
        {
            "queries": [{"role": "user", "content": "what should I remember?"}],
            "where": {},
            "method": None,
            "ranking": "salience",
        }
    ]


def test_server_retrieve_rejects_unknown_ranking_override() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_json(
            host,
            port,
            "POST",
            "/api/v3/memory/retrieve",
            {"query": "what should I remember?", "ranking": "random"},
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 400
    assert data["error"]["code"] == "bad_request"
    assert "'ranking' must be 'similarity' or 'salience'" in data["error"]["message"]


def test_server_retrieve_rejects_unknown_method_override() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_json(
            host,
            port,
            "POST",
            "/api/v3/memory/retrieve",
            {"query": "what should I remember?", "method": "hybrid"},
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 400
    assert data["error"]["code"] == "bad_request"
    assert "'method' must be 'rag' or 'llm'" in data["error"]["message"]


def test_server_retrieve_rejects_invalid_query_item() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_json(
            host,
            port,
            "POST",
            "/api/v3/memory/retrieve",
            {"queries": [123]},
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 400
    assert data["error"]["code"] == "bad_request"


def test_server_create_memory_item_endpoint() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_json(
            host,
            port,
            "POST",
            "/api/v3/memory/items/create",
            {
                "memory_type": "profile",
                "memory_content": " User prefers concise answers. ",
                "memory_categories": [" preferences ", "work_life"],
                "user": {"user_id": "u1"},
                "propagate": False,
            },
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 200
    assert data["memory_item"]["id"] == "m1"
    assert service.create_item_calls == [
        {
            "memory_type": "profile",
            "memory_content": "User prefers concise answers.",
            "memory_categories": ["preferences", "work_life"],
            "user": {"user_id": "u1"},
            "propagate": False,
        }
    ]


def test_server_update_memory_item_endpoint() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_json(
            host,
            port,
            "POST",
            "/api/v3/memory/items/update",
            {
                "memory_id": " m1 ",
                "memory_content": "Updated summary",
                "memory_categories": [],
                "user": {"user_id": "u1"},
            },
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 200
    assert data["memory_item"]["id"] == "m1"
    assert service.update_item_calls == [
        {
            "memory_id": "m1",
            "memory_type": None,
            "memory_content": "Updated summary",
            "memory_categories": [],
            "user": {"user_id": "u1"},
            "propagate": True,
        }
    ]


def test_server_delete_memory_item_endpoint() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_json(
            host,
            port,
            "POST",
            "/api/v3/memory/items/delete",
            {"memory_id": "m1", "user": {"user_id": "u1"}, "propagate": False},
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 200
    assert data["memory_item"]["id"] == "m1"
    assert service.delete_item_calls == [
        {
            "memory_id": "m1",
            "user": {"user_id": "u1"},
            "propagate": False,
        }
    ]


def test_server_create_memory_item_rejects_invalid_categories() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_json(
            host,
            port,
            "POST",
            "/api/v3/memory/items/create",
            {
                "memory_type": "profile",
                "memory_content": "User prefers concise answers.",
                "memory_categories": ["preferences", ""],
            },
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 400
    assert data["error"]["code"] == "bad_request"
    assert "'memory_categories[1]' must be a non-empty string" in data["error"]["message"]


def test_server_create_memory_item_rejects_unknown_memory_type() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_json(
            host,
            port,
            "POST",
            "/api/v3/memory/items/create",
            {
                "memory_type": "note",
                "memory_content": "User prefers concise answers.",
                "memory_categories": ["preferences"],
            },
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 400
    assert data["error"]["code"] == "bad_request"
    assert "'memory_type' must be one of: profile, event, knowledge, behavior, skill, tool" in data["error"]["message"]
    assert service.create_item_calls == []


def test_server_update_memory_item_rejects_unknown_memory_type() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_json(
            host,
            port,
            "POST",
            "/api/v3/memory/items/update",
            {"memory_id": "m1", "memory_type": "note"},
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 400
    assert data["error"]["code"] == "bad_request"
    assert "'memory_type' must be one of: profile, event, knowledge, behavior, skill, tool" in data["error"]["message"]
    assert service.update_item_calls == []


def test_server_create_memory_item_rejects_invalid_user_object() -> None:
    service = FakeMemoryService()
    with running_server(service, api_key="secret") as (host, port):
        status, data = request_json(
            host,
            port,
            "POST",
            "/api/v3/memory/items/create",
            {
                "memory_type": "profile",
                "memory_content": "User prefers concise answers.",
                "memory_categories": ["preferences"],
                "user": "u1",
            },
            headers={"Authorization": "Bearer secret"},
        )

    assert status == 400
    assert data["error"]["code"] == "bad_request"
    assert "'user' must be an object" in data["error"]["message"]
