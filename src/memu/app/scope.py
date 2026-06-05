from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Annotated, Any

from pydantic import BaseModel, TypeAdapter, ValidationError

from memu.utils.filtering import build_filter_key, normalize_filter_value, split_filter_key


def normalize_scope_where(user_model: type[BaseModel], where: Mapping[str, Any] | None) -> dict[str, Any]:
    """Validate and clean API `where` filters against the configured user model."""

    if not where:
        return {}

    valid_fields = set(getattr(user_model, "model_fields", {}).keys())
    cleaned: dict[str, Any] = {}

    for raw_key, value in where.items():
        if value is None:
            continue
        field, operator = split_filter_key(raw_key)
        if field not in valid_fields:
            msg = f"Unknown filter field '{field}' for current user scope"
            raise ValueError(msg)
        normalized_value = normalize_filter_value(field, operator, value)
        cleaned[build_filter_key(field, operator)] = _validate_scope_filter_value(
            user_model,
            field,
            operator,
            normalized_value,
        )

    return cleaned


def exact_scope_from_where(where: Mapping[str, Any] | None) -> dict[str, Any]:
    """Extract exact equality scope fields that can be used as write-time user data."""

    if not where:
        return {}
    exact: dict[str, Any] = {}
    for raw_key, value in where.items():
        if value is None:
            continue
        field, operator = split_filter_key(raw_key)
        if operator is None:
            exact[field] = value
    return exact


def concrete_scope_from_where(where: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Return a concrete write scope when a read filter targets exactly one scope."""

    if not where:
        return {}
    concrete: dict[str, Any] = {}
    for raw_key, value in where.items():
        if value is None:
            continue
        field, operator = split_filter_key(raw_key)
        if operator is not None:
            return None
        concrete[field] = value
    return concrete


def record_matches_scope(record: Any, user_scope: Mapping[str, Any] | None) -> bool:
    """Return whether a record belongs to a concrete user scope."""

    if not user_scope:
        return True
    for field, expected in user_scope.items():
        if expected is None:
            continue
        if getattr(record, str(field), None) != expected:
            return False
    return True


def scope_key_from_user(user_scope: Mapping[str, Any] | None) -> tuple[tuple[str, str], ...]:
    """Build a stable cache key for a concrete user/category scope."""

    if not user_scope:
        return ()
    return tuple(
        sorted(
            (str(field), _scope_value_key(value))
            for field, value in user_scope.items()
            if value is not None
        )
    )


def _scope_value_key(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return str(value)


def _validate_scope_filter_value(
    user_model: type[BaseModel],
    field: str,
    operator: str | None,
    value: Any,
) -> Any:
    if operator == "in":
        values = (value,) if isinstance(value, str) else tuple(value)
        return tuple(_validate_scope_field_value(user_model, field, item) for item in values)
    return _validate_scope_field_value(user_model, field, value)


def _validate_scope_field_value(user_model: type[BaseModel], field: str, value: Any) -> Any:
    try:
        model_field = user_model.model_fields[field]
        annotation = model_field.annotation
        if model_field.metadata:
            annotation = Annotated[annotation, *model_field.metadata]
        validated = TypeAdapter(annotation).validate_python(value)
    except ValidationError as exc:
        detail = exc.errors()[0]["msg"] if exc.errors() else "invalid value"
        msg = f"Invalid filter value for field '{field}': {detail}"
        raise ValueError(msg) from exc
    return validated


__all__ = [
    "concrete_scope_from_where",
    "exact_scope_from_where",
    "normalize_scope_where",
    "record_matches_scope",
    "scope_key_from_user",
]
