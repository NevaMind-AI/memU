from __future__ import annotations

import asyncio
import hmac
import json
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from pydantic import BaseModel

from memu._version import __version__
from memu.server.constants import SUPPORTED_MEMORIZE_MODALITIES, SUPPORTED_MEMORY_TYPES
from memu.server.openapi import openapi_schema
from memu.utils.retrieve import normalize_retrieve_method, normalize_retrieve_ranking
from memu.utils.serialization import model_dump_without_embeddings

if TYPE_CHECKING:
    from memu.app.service import MemoryService


MAX_REQUEST_BYTES = 10 * 1024 * 1024
PUBLIC_GET_PATHS = frozenset({"/health", "/api/v3/health", "/openapi.json", "/api/v3/openapi.json"})
POST_ROUTE_HANDLERS: Mapping[str, str] = {
    "/api/v3/memory/memorize": "_memorize",
    "/api/v3/memory/retrieve": "_retrieve",
    "/api/v3/memory/categories": "_list_categories",
    "/api/v3/memory/items": "_list_items",
    "/api/v3/memory/items/create": "_create_item",
    "/api/v3/memory/items/update": "_update_item",
    "/api/v3/memory/items/delete": "_delete_item",
    "/api/v3/memory/clear": "_clear_memory",
}
POST_PATHS = frozenset(POST_ROUTE_HANDLERS)
DELETE_PATHS = frozenset({"/api/v3/memory"})


@dataclass(frozen=True)
class MemUServerConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    api_key: str | None = None
    max_request_bytes: int = MAX_REQUEST_BYTES

    def __post_init__(self) -> None:
        object.__setattr__(self, "api_key", normalize_api_key(self.api_key))
        if self.max_request_bytes <= 0:
            raise ValueError("max_request_bytes must be positive")


def run_server(
    service: "MemoryService",
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    api_key: str | None = None,
    max_request_bytes: int = MAX_REQUEST_BYTES,
) -> None:
    """Run the built-in MemU JSON API server until interrupted."""

    handler = create_handler(
        service,
        config=MemUServerConfig(host=host, port=port, api_key=api_key, max_request_bytes=max_request_bytes),
    )
    server = ThreadingHTTPServer((host, port), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def create_handler(
    service: "MemoryService",
    *,
    config: MemUServerConfig | None = None,
) -> type[BaseHTTPRequestHandler]:
    server_config = config or MemUServerConfig()
    service_lock = threading.RLock()

    class MemURequestHandler(BaseHTTPRequestHandler):
        server_version = f"memu-server/{__version__}"

        def do_OPTIONS(self) -> None:
            path = _clean_path(self.path)
            allowed_methods = _allowed_methods_for_path(path)
            if not allowed_methods:
                self._send_error(HTTPStatus.NOT_FOUND, "not_found", f"Unknown endpoint: {path}")
                return
            allow = ",".join(allowed_methods)
            self._send_json(
                {"ok": True},
                headers={"Allow": allow, "Access-Control-Allow-Methods": allow},
            )

        def do_PUT(self) -> None:
            self._send_method_not_allowed_or_not_found()

        def do_PATCH(self) -> None:
            self._send_method_not_allowed_or_not_found()

        def do_GET(self) -> None:
            self._send_public_get_response(send_body=True)

        def do_HEAD(self) -> None:
            self._send_public_get_response(send_body=False)

        def _send_public_get_response(self, *, send_body: bool) -> None:
            path = _clean_path(self.path)
            if path in {"/health", "/api/v3/health"}:
                self._send_json(_health_payload(service, server_config), send_body=send_body)
                return
            if path in {"/openapi.json", "/api/v3/openapi.json"}:
                self._send_json(openapi_schema(), send_body=send_body)
                return
            if _allowed_methods_for_path(path):
                self._send_method_not_allowed_or_not_found(send_body=send_body)
                return
            self._send_error(HTTPStatus.NOT_FOUND, "not_found", f"Unknown endpoint: {path}", send_body=send_body)

        def do_POST(self) -> None:
            path = _clean_path(self.path)
            handler_name = POST_ROUTE_HANDLERS.get(path)
            if handler_name is None:
                self._send_method_not_allowed_or_not_found()
                return
            if not self._authorized(path):
                return

            payload = self._read_json()
            if payload is None:
                return
            try:
                with service_lock:
                    response = getattr(self, handler_name)(payload)
            except ValueError as exc:
                self._send_error(HTTPStatus.BAD_REQUEST, "bad_request", str(exc))
            except Exception as exc:  # pragma: no cover - exact service errors depend on provider/backend.
                self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error", f"{type(exc).__name__}: {exc}")
            else:
                self._send_json(response)

        def do_DELETE(self) -> None:
            path = _clean_path(self.path)
            if path not in DELETE_PATHS:
                self._send_method_not_allowed_or_not_found()
                return
            if not self._authorized(path):
                return
            payload = self._read_json(default={})
            if payload is None:
                return
            try:
                with service_lock:
                    response = asyncio.run(
                        service.clear_memory(where=_optional_mapping(payload.get("where"), field_name="where"))
                    )
            except ValueError as exc:
                self._send_error(HTTPStatus.BAD_REQUEST, "bad_request", str(exc))
            except Exception as exc:  # pragma: no cover - exact service errors depend on provider/backend.
                self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error", f"{type(exc).__name__}: {exc}")
            else:
                self._send_json(response)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

        def _memorize(self, payload: Mapping[str, Any]) -> dict[str, Any]:
            resource_url = _required_str(payload, "resource_url")
            modality = _required_choice(payload, "modality", choices=SUPPORTED_MEMORIZE_MODALITIES)
            user = _optional_mapping(payload.get("user"), field_name="user")
            result = asyncio.run(service.memorize(resource_url=resource_url, modality=modality, user=dict(user or {})))
            return {"status": "completed", "result": result}

        def _retrieve(self, payload: Mapping[str, Any]) -> dict[str, Any]:
            raw_queries = _normalize_queries(payload)
            where = _optional_mapping(payload.get("where"), field_name="where")
            method = _optional_retrieve_method(payload.get("method"))
            ranking = _optional_retrieve_ranking(payload.get("ranking"))
            return asyncio.run(
                service.retrieve(
                    queries=raw_queries,
                    where=dict(where or {}),
                    method=method,
                    ranking=ranking,
                )
            )

        def _list_categories(self, payload: Mapping[str, Any]) -> dict[str, Any]:
            where = _optional_mapping(payload.get("where"), field_name="where")
            return asyncio.run(service.list_memory_categories(where=dict(where or {})))

        def _list_items(self, payload: Mapping[str, Any]) -> dict[str, Any]:
            where = _optional_mapping(payload.get("where"), field_name="where")
            return asyncio.run(service.list_memory_items(where=dict(where or {})))

        def _create_item(self, payload: Mapping[str, Any]) -> dict[str, Any]:
            memory_type = _required_choice(payload, "memory_type", choices=SUPPORTED_MEMORY_TYPES)
            memory_content = _required_str(payload, "memory_content")
            memory_categories = _required_str_list(payload, "memory_categories")
            user = _optional_mapping(payload.get("user"), field_name="user")
            propagate = _optional_bool(payload.get("propagate"), default=True, field_name="propagate")
            return asyncio.run(
                service.create_memory_item(
                    memory_type=memory_type,
                    memory_content=memory_content,
                    memory_categories=memory_categories,
                    user=dict(user or {}),
                    propagate=propagate,
                )
            )

        def _update_item(self, payload: Mapping[str, Any]) -> dict[str, Any]:
            memory_id = _required_str(payload, "memory_id")
            memory_type = _optional_choice(
                payload.get("memory_type"),
                field_name="memory_type",
                choices=SUPPORTED_MEMORY_TYPES,
            )
            memory_content = _optional_str(payload.get("memory_content"), field_name="memory_content")
            memory_categories = _optional_str_list(payload.get("memory_categories"), field_name="memory_categories")
            user = _optional_mapping(payload.get("user"), field_name="user")
            propagate = _optional_bool(payload.get("propagate"), default=True, field_name="propagate")
            return asyncio.run(
                service.update_memory_item(
                    memory_id=memory_id,
                    memory_type=memory_type,
                    memory_content=memory_content,
                    memory_categories=memory_categories,
                    user=dict(user or {}),
                    propagate=propagate,
                )
            )

        def _delete_item(self, payload: Mapping[str, Any]) -> dict[str, Any]:
            memory_id = _required_str(payload, "memory_id")
            user = _optional_mapping(payload.get("user"), field_name="user")
            propagate = _optional_bool(payload.get("propagate"), default=True, field_name="propagate")
            return asyncio.run(
                service.delete_memory_item(
                    memory_id=memory_id,
                    user=dict(user or {}),
                    propagate=propagate,
                )
            )

        def _clear_memory(self, payload: Mapping[str, Any]) -> dict[str, Any]:
            where = _optional_mapping(payload.get("where"), field_name="where")
            return asyncio.run(service.clear_memory(where=dict(where or {})))

        def _authorized(self, path: str) -> bool:
            if path in PUBLIC_GET_PATHS:
                return True
            if not server_config.api_key:
                return True
            expected = f"Bearer {server_config.api_key}"
            if hmac.compare_digest(self.headers.get("Authorization") or "", expected):
                return True
            self._send_error(HTTPStatus.UNAUTHORIZED, "unauthorized", "Missing or invalid bearer token")
            return False

        def _read_json(self, default: Mapping[str, Any] | None = None) -> Mapping[str, Any] | None:
            length = _parse_content_length(self.headers.get("Content-Length"))
            if length is None:
                self._send_error(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_content_length",
                    "Content-Length must be a non-negative integer",
                )
                return None
            if length == 0 and default is not None:
                return default
            if length > server_config.max_request_bytes:
                self._send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request_too_large", "JSON body is too large")
                return None
            try:
                raw = self.rfile.read(length).decode("utf-8") if length else "{}"
                data = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                self._send_error(HTTPStatus.BAD_REQUEST, "invalid_json", str(exc))
                return None
            if not isinstance(data, Mapping):
                self._send_error(HTTPStatus.BAD_REQUEST, "invalid_json", "JSON body must be an object")
                return None
            return data

        def _send_json(
            self,
            payload: Mapping[str, Any],
            status: HTTPStatus = HTTPStatus.OK,
            headers: Mapping[str, str] | None = None,
            send_body: bool = True,
        ) -> None:
            body = json.dumps(payload, ensure_ascii=False, default=_json_default).encode("utf-8")
            response_headers = dict(headers or {})
            self.send_response(status.value)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header(
                "Access-Control-Allow-Methods",
                response_headers.pop("Access-Control-Allow-Methods", self._access_control_allow_methods()),
            )
            self.send_header("Access-Control-Allow-Headers", "Authorization,Content-Type")
            for name, value in response_headers.items():
                self.send_header(name, value)
            self.end_headers()
            if send_body:
                self.wfile.write(body)

        def _send_error(self, status: HTTPStatus, code: str, message: str, *, send_body: bool = True) -> None:
            self._send_json({"error": {"code": code, "message": message}}, status=status, send_body=send_body)

        def _send_method_not_allowed_or_not_found(self, *, send_body: bool = True) -> None:
            self._discard_request_body()
            path = _clean_path(self.path)
            allowed_methods = _allowed_methods_for_path(path)
            if not allowed_methods:
                self._send_error(HTTPStatus.NOT_FOUND, "not_found", f"Unknown endpoint: {path}", send_body=send_body)
                return
            allow = ",".join(allowed_methods)
            self._send_json(
                {"error": {"code": "method_not_allowed", "message": "Method not allowed"}},
                status=HTTPStatus.METHOD_NOT_ALLOWED,
                headers={"Allow": allow, "Access-Control-Allow-Methods": allow},
                send_body=send_body,
            )

        def _discard_request_body(self) -> None:
            length = _parse_content_length(self.headers.get("Content-Length"))
            if length is None or length <= 0:
                return
            remaining = length
            while remaining > 0:
                chunk = self.rfile.read(min(remaining, 64 * 1024))
                if not chunk:
                    return
                remaining -= len(chunk)

        def _access_control_allow_methods(self) -> str:
            allowed_methods = _allowed_methods_for_path(_clean_path(self.path))
            if allowed_methods:
                return ",".join(allowed_methods)
            return "GET,HEAD,POST,DELETE,OPTIONS"

    return MemURequestHandler


def _clean_path(raw_path: str) -> str:
    return urlparse(raw_path).path.rstrip("/") or "/"


def _allowed_methods_for_path(path: str) -> tuple[str, ...]:
    methods: list[str] = []
    if path in PUBLIC_GET_PATHS:
        methods.append("GET")
        methods.append("HEAD")
    if path in POST_PATHS:
        methods.append("POST")
    if path in DELETE_PATHS:
        methods.append("DELETE")
    if not methods:
        return ()
    methods.append("OPTIONS")
    return tuple(methods)


def _health_payload(service: Any, config: MemUServerConfig) -> dict[str, Any]:
    providers = _provider_summary(service)
    storage = providers.get("storage")
    metadata_store = None
    if isinstance(storage, Mapping):
        metadata_store = storage.get("metadata_store")
    if not isinstance(metadata_store, str):
        metadata_store = getattr(getattr(service.database_config, "metadata_store", None), "provider", None)
    return {
        "ok": True,
        "service": "memu-server",
        "version": __version__,
        "storage": metadata_store,
        "providers": providers,
        "auth": {"enabled": bool(config.api_key)},
        "limits": {"max_request_bytes": config.max_request_bytes},
    }


def _provider_summary(service: Any) -> dict[str, Any]:
    summary_fn = getattr(service, "_provider_summary", None)
    if callable(summary_fn):
        summary = summary_fn()
        if isinstance(summary, Mapping):
            return dict(summary)

    database_config = service.database_config
    vector_index = getattr(database_config, "vector_index", None)
    return {
        "storage": {
            "metadata_store": database_config.metadata_store.provider,
            "vector_index": getattr(vector_index, "provider", None),
        }
    }


def _parse_content_length(raw_value: str | None) -> int | None:
    if raw_value is None or raw_value == "":
        return 0
    try:
        length = int(raw_value)
    except ValueError:
        return None
    if length < 0:
        return None
    return length


def _required_str(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{key}' must be a non-empty string")
    return value.strip()


def _optional_str(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{field_name}' must be a non-empty string")
    return value.strip()


def _required_choice(payload: Mapping[str, Any], key: str, *, choices: tuple[str, ...]) -> str:
    return _choice(payload.get(key), field_name=key, choices=choices)


def _optional_choice(value: Any, *, field_name: str, choices: tuple[str, ...]) -> str | None:
    if value is None:
        return None
    return _choice(value, field_name=field_name, choices=choices)


def _choice(value: Any, *, field_name: str, choices: tuple[str, ...]) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{field_name}' must be a non-empty string")
    normalized = value.strip().lower()
    if normalized not in choices:
        raise ValueError(f"'{field_name}' must be one of: {', '.join(choices)}")
    return normalized


def _required_str_list(payload: Mapping[str, Any], key: str) -> list[str]:
    if key not in payload:
        raise ValueError(f"'{key}' must be a list of non-empty strings")
    return _str_list(payload.get(key), field_name=key)


def _optional_str_list(value: Any, *, field_name: str) -> list[str] | None:
    if value is None:
        return None
    return _str_list(value, field_name=field_name)


def _str_list(value: Any, *, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"'{field_name}' must be a list of non-empty strings")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"'{field_name}[{index}]' must be a non-empty string")
        result.append(item.strip())
    return result


def _optional_bool(value: Any, *, default: bool, field_name: str) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(f"'{field_name}' must be a boolean")
    return value


def _optional_mapping(value: Any, *, field_name: str) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"'{field_name}' must be an object")
    return value


def _optional_retrieve_method(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("'method' must be 'rag' or 'llm'")
    try:
        return normalize_retrieve_method(value, default="rag")
    except ValueError as exc:
        raise ValueError("'method' must be 'rag' or 'llm'") from exc


def _optional_retrieve_ranking(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("'ranking' must be 'similarity' or 'salience'")
    try:
        return normalize_retrieve_ranking(value, default="similarity")
    except ValueError as exc:
        raise ValueError("'ranking' must be 'similarity' or 'salience'") from exc


def _normalize_queries(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_queries = payload.get("queries")
    if raw_queries is None:
        query = payload.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("'queries' must be a non-empty list, or provide a non-empty string 'query'")
        raw_queries = [query]

    if not isinstance(raw_queries, list) or not raw_queries:
        raise ValueError("'queries' must be a non-empty list, or provide a non-empty string 'query'")

    return [_normalize_query_item(item, index=index) for index, item in enumerate(raw_queries)]


def _normalize_query_item(item: Any, *, index: int) -> dict[str, Any]:
    if isinstance(item, str):
        if not item.strip():
            raise ValueError(f"'queries[{index}]' must not be empty")
        return {"role": "user", "content": item.strip()}

    if not isinstance(item, Mapping):
        raise ValueError(f"'queries[{index}]' must be a string or an object")

    role = item.get("role", "user")
    if not isinstance(role, str) or not role.strip():
        raise ValueError(f"'queries[{index}].role' must be a non-empty string")

    content = item.get("content")
    if isinstance(content, str):
        if not content.strip():
            raise ValueError(f"'queries[{index}].content' must not be empty")
        normalized_content: str | dict[str, str] = content.strip()
    elif isinstance(content, Mapping):
        text = content.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"'queries[{index}].content.text' must be a non-empty string")
        normalized_content = {"text": text.strip()}
    else:
        raise ValueError(f"'queries[{index}].content' must be a string or an object with text")

    return {"role": role.strip(), "content": normalized_content}


def _json_default(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return model_dump_without_embeddings(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return str(value)


def normalize_api_key(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


__all__ = ["MAX_REQUEST_BYTES", "MemUServerConfig", "create_handler", "normalize_api_key", "run_server"]
