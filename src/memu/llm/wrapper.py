from __future__ import annotations

import hashlib
import inspect
import logging
import threading
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMCallContext:
    profile: str
    request_id: str
    trace_id: str | None
    operation: str | None
    step_id: str | None
    provider: str | None
    model: str | None
    tags: Mapping[str, Any] | None


@dataclass(frozen=True)
class LLMRequestView:
    kind: str
    input_items: int | None = None
    input_chars: int | None = None
    content: str | list[str] | None = None
    content_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMResponseView:
    output_items: int | None = None
    output_chars: int | None = None
    content: str | None = None
    content_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cached_input_tokens: int | None = None
    reasoning_tokens: int | None = None
    latency_ms: float | None = None
    finish_reason: str | None = None
    status: str | None = None
    tokens_breakdown: dict[str, Any] | None = None


@dataclass(frozen=True)
class LLMCallFilter:
    operations: set[str] | None = None
    step_ids: set[str] | None = None
    providers: set[str] | None = None
    models: set[str] | None = None
    statuses: set[str] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "operations", _normalize_set(self.operations))
        object.__setattr__(self, "providers", _normalize_set(self.providers))
        object.__setattr__(self, "models", _normalize_set(self.models))
        object.__setattr__(self, "statuses", _normalize_set(self.statuses))

    def matches(self, ctx: LLMCallContext, status: str | None) -> bool:
        if self.operations and (ctx.operation or "").lower() not in self.operations:
            return False
        if self.step_ids and (ctx.step_id or "") not in self.step_ids:
            return False
        if self.providers and (ctx.provider or "").lower() not in self.providers:
            return False
        if self.models and (ctx.model or "").lower() not in self.models:
            return False
        if self.statuses:
            return status is not None and status.lower() in self.statuses
        return True


@dataclass(frozen=True)
class LLMCallMetadata:
    profile: str | None = None
    operation: str | None = None
    step_id: str | None = None
    trace_id: str | None = None
    tags: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class _LLMInterceptor:
    interceptor_id: int
    fn: Callable[..., Any]
    name: str | None
    priority: int
    order: int
    filter: LLMCallFilter | Callable[[LLMCallContext, str | None], bool] | None


@dataclass(frozen=True)
class _LLMInterceptorSnapshot:
    before: tuple[_LLMInterceptor, ...]
    after: tuple[_LLMInterceptor, ...]
    on_error: tuple[_LLMInterceptor, ...]


class LLMInterceptorHandle:
    def __init__(self, registry: LLMInterceptorRegistry, interceptor_id: int) -> None:
        self._registry = registry
        self._interceptor_id = interceptor_id
        self._disposed = False

    def dispose(self) -> bool:
        if self._disposed:
            return False
        self._disposed = True
        return self._registry.remove(self._interceptor_id)


class LLMInterceptorRegistry:
    def __init__(self, *, strict: bool = False) -> None:
        self._before: tuple[_LLMInterceptor, ...] = ()
        self._after: tuple[_LLMInterceptor, ...] = ()
        self._on_error: tuple[_LLMInterceptor, ...] = ()
        self._lock = threading.Lock()
        self._seq = 0
        self._strict = strict

    @property
    def strict(self) -> bool:
        return self._strict

    def register_before(
        self,
        fn: Callable[..., Any],
        *,
        name: str | None = None,
        priority: int = 0,
        where: LLMCallFilter | Callable[[LLMCallContext, str | None], bool] | Mapping[str, Any] | None = None,
    ) -> LLMInterceptorHandle:
        return self._register("before", fn, name=name, priority=priority, where=where)

    def register_after(
        self,
        fn: Callable[..., Any],
        *,
        name: str | None = None,
        priority: int = 0,
        where: LLMCallFilter | Callable[[LLMCallContext, str | None], bool] | Mapping[str, Any] | None = None,
    ) -> LLMInterceptorHandle:
        return self._register("after", fn, name=name, priority=priority, where=where)

    def register_on_error(
        self,
        fn: Callable[..., Any],
        *,
        name: str | None = None,
        priority: int = 0,
        where: LLMCallFilter | Callable[[LLMCallContext, str | None], bool] | Mapping[str, Any] | None = None,
    ) -> LLMInterceptorHandle:
        return self._register("on_error", fn, name=name, priority=priority, where=where)

    def _register(
        self,
        kind: str,
        fn: Callable[..., Any],
        *,
        name: str | None,
        priority: int,
        where: LLMCallFilter | Callable[[LLMCallContext, str | None], bool] | Mapping[str, Any] | None,
    ) -> LLMInterceptorHandle:
        if not callable(fn):
            msg = "Interceptor must be callable"
            raise TypeError(msg)
        where = _coerce_filter(where)
        with self._lock:
            self._seq += 1
            interceptor = _LLMInterceptor(
                interceptor_id=self._seq,
                fn=fn,
                name=name,
                priority=priority,
                order=self._seq,
                filter=where,
            )
            if kind == "before":
                self._before = _sorted_interceptors(self._before, interceptor)
            elif kind == "after":
                self._after = _sorted_interceptors(self._after, interceptor)
            elif kind == "on_error":
                self._on_error = _sorted_interceptors(self._on_error, interceptor)
            else:
                msg = f"Unknown interceptor kind '{kind}'"
                raise ValueError(msg)
        return LLMInterceptorHandle(self, interceptor.interceptor_id)

    def remove(self, interceptor_id: int) -> bool:
        with self._lock:
            removed = False
            before = tuple(i for i in self._before if i.interceptor_id != interceptor_id)
            after = tuple(i for i in self._after if i.interceptor_id != interceptor_id)
            on_error = tuple(i for i in self._on_error if i.interceptor_id != interceptor_id)
            if len(before) != len(self._before):
                removed = True
                self._before = before
            if len(after) != len(self._after):
                removed = True
                self._after = after
            if len(on_error) != len(self._on_error):
                removed = True
                self._on_error = on_error
        return removed

    def snapshot(self) -> _LLMInterceptorSnapshot:
        return _LLMInterceptorSnapshot(self._before, self._after, self._on_error)


class LLMClientWrapper:
    def __init__(
        self,
        client: Any,
        *,
        registry: LLMInterceptorRegistry,
        metadata: LLMCallMetadata | None = None,
        provider: str | None = None,
        chat_model: str | None = None,
        embed_model: str | None = None,
    ) -> None:
        self._client = client
        self._registry = registry
        self._metadata = metadata or LLMCallMetadata()
        self._provider = provider
        self._chat_model = chat_model or getattr(client, "chat_model", None)
        self._embed_model = embed_model or getattr(client, "embed_model", None)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)

    async def summarize(
        self,
        text: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> Any:
        request_view = _build_text_request_view(
            "summarize",
            text,
            metadata={
                "system_prompt_chars": len(system_prompt or ""),
                "max_tokens": max_tokens,
            },
        )

        async def _call() -> Any:
            return await self._client.summarize(text, max_tokens=max_tokens, system_prompt=system_prompt)

        return await self._invoke(
            kind="summarize",
            call_fn=_call,
            request_view=request_view,
            model=self._chat_model,
            response_builder=_build_text_response_view,
        )

    async def vision(
        self,
        prompt: str,
        image_path: str,
        *,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> Any:
        metadata = {
            "image_path": Path(image_path).name,
            "image_bytes": _safe_file_size(image_path),
            "system_prompt_chars": len(system_prompt or ""),
            "max_tokens": max_tokens,
        }
        request_view = _build_text_request_view("vision", prompt, metadata=metadata)

        async def _call() -> Any:
            return await self._client.vision(
                prompt,
                image_path,
                max_tokens=max_tokens,
                system_prompt=system_prompt,
            )

        return await self._invoke(
            kind="vision",
            call_fn=_call,
            request_view=request_view,
            model=self._chat_model,
            response_builder=_build_text_response_view,
        )

    async def embed(self, inputs: list[str]) -> Any:
        request_view = _build_embedding_request_view(inputs)

        async def _call() -> Any:
            return await self._client.embed(inputs)

        return await self._invoke(
            kind="embed",
            call_fn=_call,
            request_view=request_view,
            model=self._embed_model,
            response_builder=_build_embedding_response_view,
        )

    async def transcribe(
        self,
        audio_path: str,
        *,
        prompt: str | None = None,
        language: str | None = None,
        response_format: str = "text",
    ) -> Any:
        metadata = {
            "audio_path": Path(audio_path).name,
            "audio_bytes": _safe_file_size(audio_path),
            "prompt_chars": len(prompt or ""),
            "language": language,
            "response_format": response_format,
        }
        request_view = _build_text_request_view("transcribe", prompt or "", metadata=metadata)

        async def _call() -> Any:
            return await self._client.transcribe(
                audio_path,
                prompt=prompt,
                language=language,
                response_format=response_format,
            )

        return await self._invoke(
            kind="transcribe",
            call_fn=_call,
            request_view=request_view,
            model=None,
            response_builder=_build_text_response_view,
        )

    async def _invoke(
        self,
        *,
        kind: str,
        call_fn: Callable[[], Any],
        request_view: LLMRequestView,
        model: str | None,
        response_builder: Callable[[Any], LLMResponseView],
    ) -> Any:
        call_ctx = self._build_call_context(model)
        snapshot = self._registry.snapshot()
        await self._run_before(snapshot.before, call_ctx, request_view)
        start_time = time.perf_counter()
        try:
            result = call_fn()
            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000
            usage = LLMUsage(latency_ms=latency_ms, status="error")
            await self._run_on_error(snapshot.on_error, call_ctx, request_view, exc, usage)
            raise
        else:
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Handle tuple response: (pure_response, raw_response)
            pure_result = result
            raw_response = None
            if isinstance(result, tuple) and len(result) == 2:
                pure_result, raw_response = result

            response_view = response_builder(pure_result)

            # Extract token usage from raw response (best-effort)
            extracted_usage = _extract_usage_from_raw_response(kind=kind, raw_response=raw_response)
            usage = LLMUsage(
                input_tokens=extracted_usage.get("input_tokens"),
                output_tokens=extracted_usage.get("output_tokens"),
                total_tokens=extracted_usage.get("total_tokens"),
                cached_input_tokens=extracted_usage.get("cached_input_tokens"),
                reasoning_tokens=extracted_usage.get("reasoning_tokens"),
                latency_ms=latency_ms,
                finish_reason=extracted_usage.get("finish_reason"),
                status="success",
                tokens_breakdown=extracted_usage.get("tokens_breakdown"),
            )

            await self._run_after(snapshot.after, call_ctx, request_view, response_view, usage)
            return pure_result

    def _build_call_context(self, model: str | None) -> LLMCallContext:
        request_id = uuid.uuid4().hex
        return LLMCallContext(
            profile=self._metadata.profile or "",
            request_id=request_id,
            trace_id=self._metadata.trace_id,
            operation=self._metadata.operation,
            step_id=self._metadata.step_id,
            provider=self._provider,
            model=model,
            tags=self._metadata.tags,
        )

    async def _run_before(
        self,
        interceptors: Sequence[_LLMInterceptor],
        ctx: LLMCallContext,
        request_view: LLMRequestView,
    ) -> None:
        for interceptor in interceptors:
            if not _should_run_interceptor(interceptor, ctx, None):
                continue
            await _safe_invoke_interceptor(
                interceptor,
                self._registry.strict,
                ctx,
                request_view,
            )

    async def _run_after(
        self,
        interceptors: Sequence[_LLMInterceptor],
        ctx: LLMCallContext,
        request_view: LLMRequestView,
        response_view: LLMResponseView,
        usage: LLMUsage,
    ) -> None:
        for interceptor in reversed(interceptors):
            if not _should_run_interceptor(interceptor, ctx, "success"):
                continue
            await _safe_invoke_interceptor(
                interceptor,
                self._registry.strict,
                ctx,
                request_view,
                response_view,
                usage,
            )

    async def _run_on_error(
        self,
        interceptors: Sequence[_LLMInterceptor],
        ctx: LLMCallContext,
        request_view: LLMRequestView,
        error: Exception,
        usage: LLMUsage,
    ) -> None:
        for interceptor in reversed(interceptors):
            if not _should_run_interceptor(interceptor, ctx, "error"):
                continue
            await _safe_invoke_interceptor(
                interceptor,
                self._registry.strict,
                ctx,
                request_view,
                error,
                usage,
            )


def _normalize_set(values: set[str] | None) -> set[str] | None:
    if not values:
        return None
    return {str(value).lower() for value in values}


def _sorted_interceptors(
    existing: tuple[_LLMInterceptor, ...],
    interceptor: _LLMInterceptor,
) -> tuple[_LLMInterceptor, ...]:
    items = list(existing)
    items.append(interceptor)
    items.sort(key=lambda item: (item.priority, item.order))
    return tuple(items)


def _hash_text(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_texts(values: Sequence[str]) -> str | None:
    if not values:
        return None
    sha = hashlib.sha256()
    for value in values:
        sha.update(value.encode("utf-8"))
        sha.update(b"\0")
    return sha.hexdigest()


def _safe_file_size(path: str) -> int | None:
    try:
        return Path(path).stat().st_size
    except OSError:
        return None


def _build_text_request_view(
    kind: str,
    text: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> LLMRequestView:
    return LLMRequestView(
        kind=kind,
        input_items=1,
        input_chars=len(text),
        content=text,
        content_hash=_hash_text(text),
        metadata=metadata or {},
    )


def _build_text_response_view(response: str) -> LLMResponseView:
    return LLMResponseView(
        output_items=1,
        output_chars=len(response),
        content=response,
        content_hash=_hash_text(response),
        metadata={},
    )


def _build_embedding_request_view(inputs: Sequence[str]) -> LLMRequestView:
    total_chars = sum(len(text) for text in inputs)
    return LLMRequestView(
        kind="embed",
        input_items=len(inputs),
        input_chars=total_chars,
        content=list(inputs),
        content_hash=_hash_texts(inputs),
        metadata={},
    )


def _build_embedding_response_view(response: Sequence[Sequence[float]]) -> LLMResponseView:
    vector_dim = len(response[0]) if response else 0
    return LLMResponseView(
        output_items=len(response),
        output_chars=None,
        content_hash=None,
        metadata={"vector_dim": vector_dim},
    )


def _get_attr_or_key(obj: Any, key: str) -> Any:
    """Extract value from object attribute or dict key."""
    if obj is None:
        return None
    if hasattr(obj, key):
        return getattr(obj, key)
    if isinstance(obj, dict):
        return obj.get(key)
    return None


def _extract_finish_reason(raw_response: Any) -> str | None:
    """Extract finish_reason from choices[0] if available."""
    choices = _get_attr_or_key(raw_response, "choices")
    if choices and len(choices) > 0:
        result = _get_attr_or_key(choices[0], "finish_reason")
        return str(result) if result is not None else None
    return None


def _get_usage_object(raw_response: Any) -> Any:
    """Get usage object/dict from response."""
    if hasattr(raw_response, "usage") and raw_response.usage is not None:
        return raw_response.usage
    if isinstance(raw_response, dict) and "usage" in raw_response:
        return raw_response["usage"]
    return None


def _convert_to_dict(obj: Any) -> dict[str, Any] | None:
    """Convert object to dict using available methods."""
    if hasattr(obj, "model_dump"):
        result: dict[str, Any] = obj.model_dump()
        return result
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    if isinstance(obj, dict):
        return obj
    return None


def _extract_token_details(usage_obj: Any, usage_data: dict[str, Any]) -> None:
    """Extract token breakdown and cached tokens from usage object."""
    completion_tokens_details = _get_attr_or_key(usage_obj, "completion_tokens_details")
    if completion_tokens_details is not None:
        breakdown = _convert_to_dict(completion_tokens_details)
        if breakdown is not None:
            usage_data["tokens_breakdown"] = breakdown
        reasoning_tokens = _get_attr_or_key(completion_tokens_details, "reasoning_tokens")
        if reasoning_tokens is not None:
            usage_data["reasoning_tokens"] = reasoning_tokens

    prompt_tokens_details = _get_attr_or_key(usage_obj, "prompt_tokens_details")
    if prompt_tokens_details is not None:
        cached_tokens = _get_attr_or_key(prompt_tokens_details, "cached_tokens")
        if cached_tokens is not None:
            usage_data["cached_input_tokens"] = cached_tokens


def _extract_usage_from_raw_response(kind: str, raw_response: Any) -> dict[str, Any]:
    """
    Best-effort extraction of token usage from raw LLM response.

    Supports OpenAI SDK response objects and JSON dict responses.
    Mapping:
        input_tokens <- prompt_tokens
        output_tokens <- completion_tokens
        total_tokens <- total_tokens
        tokens_breakdown <- completion_tokens_details
    """
    usage_data: dict[str, Any] = {}

    if raw_response is None:
        return usage_data

    try:
        finish_reason = _extract_finish_reason(raw_response)
        if finish_reason is not None:
            usage_data["finish_reason"] = finish_reason

        usage_obj = _get_usage_object(raw_response)
        if usage_obj is None:
            return usage_data

        # Map prompt_tokens -> input_tokens
        prompt_tokens = _get_attr_or_key(usage_obj, "prompt_tokens")
        if prompt_tokens is not None:
            usage_data["input_tokens"] = prompt_tokens

        # Map completion_tokens -> output_tokens
        completion_tokens = _get_attr_or_key(usage_obj, "completion_tokens")
        if completion_tokens is not None:
            usage_data["output_tokens"] = completion_tokens

        # total_tokens stays the same
        total_tokens = _get_attr_or_key(usage_obj, "total_tokens")
        if total_tokens is not None:
            usage_data["total_tokens"] = total_tokens

        # Some providers does not explicitly return input_tokens for embedding calls
        if kind == "embed" and usage_data.get("total_tokens") and not usage_data.get("input_tokens"):
            usage_data["input_tokens"] = usage_data["total_tokens"]

        _extract_token_details(usage_obj, usage_data)

    except Exception:
        # Best-effort: silently ignore extraction errors
        logger.debug("Failed to extract usage from raw response", exc_info=True)

    return usage_data


def _coerce_filter(
    where: LLMCallFilter | Callable[[LLMCallContext, str | None], bool] | Mapping[str, Any] | None,
) -> LLMCallFilter | Callable[[LLMCallContext, str | None], bool] | None:
    if where is None or callable(where) or isinstance(where, LLMCallFilter):
        return where
    if isinstance(where, Mapping):
        return LLMCallFilter(
            operations=_ensure_set(where.get("operations") or where.get("operation")),
            step_ids=_ensure_set(where.get("step_ids") or where.get("step_id")),
            providers=_ensure_set(where.get("providers") or where.get("provider")),
            models=_ensure_set(where.get("models") or where.get("model")),
            statuses=_ensure_set(where.get("statuses") or where.get("status")),
        )
    msg = "Filter must be a callable, mapping, or LLMCallFilter"
    raise TypeError(msg)


def _ensure_set(value: Any) -> set[str] | None:
    if value is None:
        return None
    if isinstance(value, set):
        return {str(item) for item in value}
    if isinstance(value, (list, tuple)):
        return {str(item) for item in value}
    return {str(value)}


def _should_run_interceptor(
    interceptor: _LLMInterceptor,
    ctx: LLMCallContext,
    status: str | None,
) -> bool:
    filt = interceptor.filter
    if filt is None:
        return True
    if isinstance(filt, LLMCallFilter):
        try:
            return filt.matches(ctx, status)
        except Exception:
            logger.exception("LLM interceptor filter failed: %s", interceptor.name or interceptor.interceptor_id)
            return False
    try:
        return bool(filt(ctx, status))
    except TypeError:
        try:
            return bool(filt(ctx, None))
        except Exception:
            logger.exception("LLM interceptor filter failed: %s", interceptor.name or interceptor.interceptor_id)
            return False
    except Exception:
        logger.exception("LLM interceptor filter failed: %s", interceptor.name or interceptor.interceptor_id)
        return False


async def _safe_invoke_interceptor(
    interceptor: _LLMInterceptor,
    strict: bool,
    *args: Any,
) -> None:
    try:
        result = interceptor.fn(*args)
        if inspect.isawaitable(result):
            await result
    except Exception:
        if strict:
            raise
        logger.exception("LLM interceptor failed: %s", interceptor.name or interceptor.interceptor_id)
