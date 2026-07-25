from __future__ import annotations

import asyncio
from collections.abc import Mapping
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from memu.embedding.http_client import proxy_bypass_mounts
from memu.env import env

DEFAULT_CLOUD_BASE_URL = "https://api.memu.so/api/v4/memory/"
DEFAULT_SCOPE = "default"

_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
_USER_FIELDS = {"user_id", "agent_id", "user_name", "agent_name"}
_WHERE_FIELDS = {"user_id", "agent_id"}


class CloudMemoryError(RuntimeError):
    """Base error raised by the memU cloud transport."""

    def __init__(self, message: str, *, status_code: int | None = None, code: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class CloudClientConfigurationError(ValueError):
    """Cloud client configuration or argument validation failed."""

    @classmethod
    def empty_api_key(cls) -> CloudClientConfigurationError:
        return cls("MEMU_CLOUD_API_KEY must not be empty")

    @classmethod
    def invalid_attempts(cls) -> CloudClientConfigurationError:
        return cls("max_attempts must be at least 1")

    @classmethod
    def unsupported_where(cls, fields: list[str]) -> CloudClientConfigurationError:
        joined = ", ".join(fields)
        return cls(
            f"Cloud memory only supports exact user_id and agent_id filters; unsupported where field(s): {joined}"
        )

    @classmethod
    def unsupported_user(cls, fields: list[str]) -> CloudClientConfigurationError:
        joined = ", ".join(fields)
        return cls(f"Cloud memory does not support user field(s): {joined}")


class CloudAuthenticationError(CloudMemoryError):
    """The project API key is absent or invalid."""


class CloudAuthorizationError(CloudMemoryError):
    """The project API key cannot perform the requested operation."""


class CloudValidationError(CloudMemoryError):
    """The cloud API rejected the request payload or query."""


class CloudRateLimitError(CloudMemoryError):
    """The cloud API remained rate-limited after safe retries."""


class CloudTransportError(CloudMemoryError):
    """The cloud API could not be reached."""

    @classmethod
    def from_transport(cls, exc: Exception) -> CloudTransportError:
        return cls(f"memU cloud transport failed: {exc}")


class CloudServiceError(CloudMemoryError):
    """The cloud API returned an unexpected failure response."""

    @classmethod
    def invalid_json(cls, status_code: int) -> CloudServiceError:
        return cls(f"memU cloud returned invalid JSON ({status_code})", status_code=status_code)

    @classmethod
    def unexpected_shape(cls, status_code: int) -> CloudServiceError:
        return cls(f"memU cloud returned an unexpected response shape ({status_code})", status_code=status_code)

    @classmethod
    def unreachable_retry_state(cls) -> CloudServiceError:
        return cls("cloud request retry loop exited unexpectedly")


class CloudMemoryClient:
    """HTTP implementation of the three agentic memory operations."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_CLOUD_BASE_URL,
        api_key: str,
        timeout: httpx.Timeout | None = None,
        max_attempts: int = 3,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise CloudClientConfigurationError.empty_api_key()
        if max_attempts < 1:
            raise CloudClientConfigurationError.invalid_attempts()
        self.base_url = base_url.rstrip("/") + "/"
        self.api_key = api_key
        self.timeout = timeout or httpx.Timeout(30.0, connect=5.0)
        self.max_attempts = max_attempts
        self.transport = transport

    async def list_all_recall_files(
        self,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._request("GET", "", params=self._scope(where))

    async def progressive_retrieve(
        self,
        query: str,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"query": query, **self._scope(where)}
        return await self._request("POST", "search", json=payload)

    async def commit_results(
        self,
        *,
        recall_files: list[dict[str, Any]] | None = None,
        resource: list[dict[str, Any]] | None = None,
        user: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "user": self._user(user),
            "recall_files": recall_files or [],
            "resource": resource or [],
        }
        return await self._request("POST", "", json=payload)

    @staticmethod
    def _scope(where: Mapping[str, Any] | None) -> dict[str, str]:
        values = dict(where or {})
        unsupported = sorted(set(values) - _WHERE_FIELDS)
        if unsupported:
            raise CloudClientConfigurationError.unsupported_where(unsupported)
        return {
            "user_id": CloudMemoryClient._scope_value(values.get("user_id")),
            "agent_id": CloudMemoryClient._scope_value(values.get("agent_id")),
        }

    @staticmethod
    def _scope_value(value: Any) -> str:
        if value is None:
            return DEFAULT_SCOPE
        resolved = str(value).strip()
        return resolved or DEFAULT_SCOPE

    @staticmethod
    def _user(user: Mapping[str, Any] | None) -> dict[str, Any]:
        values = dict(user or {})
        unsupported = sorted(set(values) - _USER_FIELDS)
        if unsupported:
            raise CloudClientConfigurationError.unsupported_user(unsupported)
        payload: dict[str, Any] = {
            "user_id": CloudMemoryClient._scope_value(values.get("user_id")),
            "agent_id": CloudMemoryClient._scope_value(values.get("agent_id")),
        }
        for field in ("user_name", "agent_name"):
            if field in values:
                payload[field] = values[field]
        return payload

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        explicit_proxy = env("MEMU_HTTP_PROXY") or None
        mounts = proxy_bypass_mounts(self.base_url) if explicit_proxy is None else None
        client_kwargs: dict[str, Any] = {
            "base_url": self.base_url,
            "timeout": self.timeout,
            "headers": headers,
            "transport": self.transport,
            "trust_env": self.transport is None,
            "follow_redirects": True,
        }
        if self.transport is None:
            client_kwargs["proxy"] = explicit_proxy
            client_kwargs["mounts"] = mounts

        # httpx normalizes ``base_url`` to a trailing slash for relative URL
        # joining, while the public collection route is slashless. The service
        # returns 404 (not a redirect) for ``/api/v4/memory/``, so root
        # operations must use the absolute collection URL without that slash.
        request_target = endpoint or self.base_url.rstrip("/")
        async with httpx.AsyncClient(**client_kwargs) as client:
            for attempt in range(1, self.max_attempts + 1):
                try:
                    response = await client.request(method, request_target, params=params, json=json)
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    if attempt < self.max_attempts:
                        await asyncio.sleep(self._retry_delay(attempt))
                        continue
                    raise CloudTransportError.from_transport(exc) from exc

                if response.status_code in _RETRYABLE_STATUS_CODES and attempt < self.max_attempts:
                    await asyncio.sleep(self._retry_delay(attempt, response))
                    continue
                if response.is_error:
                    raise self._response_error(response)
                try:
                    data = response.json()
                except ValueError as exc:
                    raise CloudServiceError.invalid_json(response.status_code) from exc
                if not isinstance(data, dict):
                    raise CloudServiceError.unexpected_shape(response.status_code)
                return data

        raise CloudServiceError.unreachable_retry_state()

    @staticmethod
    def _retry_delay(attempt: int, response: httpx.Response | None = None) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return min(max(float(retry_after), 0.0), 30.0)
                except ValueError:
                    try:
                        retry_at = parsedate_to_datetime(retry_after)
                        now = parsedate_to_datetime(response.headers.get("Date", ""))
                        return float(min(max((retry_at - now).total_seconds(), 0.0), 30.0))
                    except (TypeError, ValueError, OverflowError):
                        pass
        return float(min(0.25 * (2 ** (attempt - 1)), 2.0))

    @staticmethod
    def _response_error(response: httpx.Response) -> CloudMemoryError:
        message, code = CloudMemoryClient._error_details(response)
        error_type, label = CloudMemoryClient._error_category(response.status_code)
        suffix = f" [{code}]" if code else ""
        return error_type(
            f"memU cloud {label} ({response.status_code}): {message}{suffix}",
            status_code=response.status_code,
            code=code,
        )

    @staticmethod
    def _error_details(response: httpx.Response) -> tuple[str, str | None]:
        message = response.reason_phrase or "request failed"
        code: str | None = None
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            if isinstance(payload.get("message"), str) and payload["message"].strip():
                message = payload["message"].strip()
            details = payload.get("details")
            if isinstance(details, list):
                for detail in details:
                    if isinstance(detail, dict) and isinstance(detail.get("code"), str):
                        code = detail["code"]
                        break
        return message, code

    @staticmethod
    def _error_category(status: int) -> tuple[type[CloudMemoryError], str]:
        if status == 401:
            return CloudAuthenticationError, "authentication failed"
        if status == 403:
            return CloudAuthorizationError, "authorization failed"
        if status in {400, 409, 422}:
            return CloudValidationError, "request rejected"
        if status == 429:
            return CloudRateLimitError, "rate limit exceeded"
        return CloudServiceError, "service request failed"
