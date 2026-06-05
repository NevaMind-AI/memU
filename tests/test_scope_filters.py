from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from memu.app.scope import (
    concrete_scope_from_where,
    exact_scope_from_where,
    normalize_scope_where,
    record_matches_scope,
    scope_key_from_user,
)
from memu.utils.filtering import normalize_filter_value, split_filter_key

ROOT = Path(__file__).resolve().parents[1]


class UserScope(BaseModel):
    user_id: str | None = None
    agent_id: str | None = None


class TenantScope(BaseModel):
    tenant_id: int | None = None
    user_id: str | None = None


class RequiredTenantScope(BaseModel):
    tenant_id: int
    user_id: str


class ConstrainedScope(BaseModel):
    user_id: str = Field(min_length=2)


class ScopedRecord:
    def __init__(self, **values: object) -> None:
        for key, value in values.items():
            setattr(self, key, value)


def _assert_value_error(func: Any, expected: str) -> None:
    try:
        func()
    except ValueError as exc:
        assert expected in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_normalize_scope_where_accepts_equality_and_in_filters() -> None:
    where = normalize_scope_where(
        UserScope,
        {
            "user_id": "u1",
            "agent_id__in": ["agent-a", "agent-b"],
            "agent_id": None,
        },
    )

    assert where == {
        "user_id": "u1",
        "agent_id__in": ("agent-a", "agent-b"),
    }


def test_normalize_scope_where_validates_and_normalizes_values_with_user_model() -> None:
    where = normalize_scope_where(
        TenantScope,
        {
            "tenant_id": "42",
            "tenant_id__in": ["1", 2],
            "user_id__in": "u1",
        },
    )

    assert where == {
        "tenant_id": 42,
        "tenant_id__in": (1, 2),
        "user_id__in": ("u1",),
    }


def test_normalize_scope_where_validates_single_fields_without_requiring_full_model() -> None:
    where = normalize_scope_where(RequiredTenantScope, {"tenant_id": "42"})

    assert where == {"tenant_id": 42}


def test_normalize_scope_where_rejects_unknown_scope_fields() -> None:
    _assert_value_error(
        lambda: normalize_scope_where(UserScope, {"session_id": "s1"}),
        "Unknown filter field 'session_id'",
    )


def test_normalize_scope_where_rejects_unsupported_filter_operators() -> None:
    _assert_value_error(
        lambda: normalize_scope_where(UserScope, {"user_id__ne": "u1"}),
        "Unsupported filter operator '__ne'",
    )


def test_normalize_scope_where_rejects_non_iterable_in_filter_values() -> None:
    _assert_value_error(
        lambda: normalize_scope_where(UserScope, {"user_id__in": 123}),
        "Filter 'user_id__in' must be a string or an iterable of values",
    )


def test_normalize_scope_where_rejects_values_invalid_for_user_model() -> None:
    _assert_value_error(
        lambda: normalize_scope_where(TenantScope, {"tenant_id": "not-an-int"}),
        "Invalid filter value for field 'tenant_id'",
    )
    _assert_value_error(
        lambda: normalize_scope_where(TenantScope, {"tenant_id__in": ["1", "not-an-int"]}),
        "Invalid filter value for field 'tenant_id'",
    )
    _assert_value_error(
        lambda: normalize_scope_where(ConstrainedScope, {"user_id": "x"}),
        "Invalid filter value for field 'user_id'",
    )


def test_split_filter_key_rejects_empty_filter_fields() -> None:
    _assert_value_error(lambda: split_filter_key(""), "Filter field must be a non-empty string")
    _assert_value_error(lambda: split_filter_key("__in"), "Filter field must be a non-empty string")


def test_in_filter_preserves_string_as_single_value() -> None:
    field, operator = split_filter_key("user_id__in")

    assert (field, operator) == ("user_id", "in")
    assert normalize_filter_value(field, operator, "u1") == "u1"


def test_scope_key_from_user_is_stable_and_ignores_none_values() -> None:
    assert scope_key_from_user({"agent_id": None, "user_id": "u1"}) == (("user_id", '"u1"'),)
    assert scope_key_from_user({"user_id": "u1", "agent_id": "a1"}) == (
        ("agent_id", '"a1"'),
        ("user_id", '"u1"'),
    )


def test_exact_scope_from_where_uses_only_equality_filters() -> None:
    assert exact_scope_from_where({"user_id": "u1", "agent_id__in": ["a1", "a2"], "session_id": None}) == {
        "user_id": "u1"
    }


def test_concrete_scope_from_where_requires_single_exact_scope() -> None:
    assert concrete_scope_from_where(None) == {}
    assert concrete_scope_from_where({"user_id": "u1", "agent_id": "a1"}) == {"user_id": "u1", "agent_id": "a1"}
    assert concrete_scope_from_where({"user_id": "u1", "agent_id__in": ("a1", "a2")}) is None


def test_record_matches_scope_requires_all_non_null_scope_fields() -> None:
    record = ScopedRecord(user_id="u1", agent_id="a1")

    assert record_matches_scope(record, {"user_id": "u1", "agent_id": "a1"})
    assert record_matches_scope(record, {"user_id": "u1", "agent_id": None})
    assert not record_matches_scope(record, {"user_id": "u2"})
    assert not record_matches_scope(record, {"user_id": "u1", "agent_id": "a2"})


def test_backend_records_preserve_scope_extras_for_sqlite_cache() -> None:
    models_source = (ROOT / "src" / "memu" / "database" / "models.py").read_text(encoding="utf-8")
    base_record = _class_node(models_source, "BaseRecord")
    model_config = _class_assignment(base_record, "model_config")

    assert isinstance(model_config, ast.Call)
    assert getattr(model_config.func, "id", "") == "ConfigDict"
    assert any(
        keyword.arg == "extra"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value == "allow"
        for keyword in model_config.keywords
    )

    sqlite_paths = [
        "src/memu/database/sqlite/repositories/resource_repo.py",
        "src/memu/database/sqlite/repositories/memory_category_repo.py",
        "src/memu/database/sqlite/repositories/memory_item_repo.py",
        "src/memu/database/sqlite/repositories/category_item_repo.py",
    ]
    for relative_path in sqlite_paths:
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "**self._scope_kwargs_from(row)" in source or "**self._scope_kwargs_from(existing)" in source


def test_persistent_category_schema_enforces_name_uniqueness_per_scope() -> None:
    checked = [
        ("src/memu/database/sqlite/schema.py", "build_sqlite_table_model"),
        ("src/memu/database/postgres/schema.py", "build_table_model"),
    ]

    for relative_path, builder_name in checked:
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        call = _assignment_call(source, "memory_category_model", builder_name)
        keyword_values = {keyword.arg: keyword.value for keyword in call.keywords}

        assert "unique_with_scope" in keyword_values
        assert ast.unparse(keyword_values["unique_with_scope"]) == "['name']"


def test_category_context_is_cached_per_scope() -> None:
    service_source = (ROOT / "src" / "memu" / "app" / "service.py").read_text(encoding="utf-8")
    memorize_source = (ROOT / "src" / "memu" / "app" / "memorize.py").read_text(encoding="utf-8")

    assert "category_scope_key" in service_source
    assert "category_cache" in service_source
    assert "scope_key = scope_key_from_user(user_scope)" in memorize_source
    assert "ctx.category_cache[scope_key]" in memorize_source


def test_patch_update_and_delete_guard_memory_items_by_user_scope() -> None:
    crud_source = (ROOT / "src" / "memu" / "app" / "crud.py").read_text(encoding="utf-8")
    patch_source = (ROOT / "src" / "memu" / "app" / "patch.py").read_text(encoding="utf-8")

    assert "record_matches_scope" in crud_source
    assert "record_matches_scope" in patch_source
    assert "self._ensure_item_matches_user_scope(item, user, memory_id)" in crud_source
    assert 'self._ensure_item_matches_user_scope(item, state["user"], memory_id)' in crud_source
    assert "self._ensure_item_matches_user_scope(item, user, memory_id)" in patch_source
    assert 'self._ensure_item_matches_user_scope(item, state["user"], memory_id)' in patch_source


def test_first_run_category_bootstrap_uses_concrete_scope_only() -> None:
    crud_source = (ROOT / "src" / "memu" / "app" / "crud.py").read_text(encoding="utf-8")
    retrieve_source = (ROOT / "src" / "memu" / "app" / "retrieve.py").read_text(encoding="utf-8")
    list_items_source = _async_function_source(crud_source, "list_memory_items")
    list_categories_source = _async_function_source(crud_source, "list_memory_categories")
    retrieve_fn_source = _async_function_source(retrieve_source, "retrieve")

    assert "bootstrap_scope = concrete_scope_from_where(where_filters)" not in list_items_source
    assert "bootstrap_scope = concrete_scope_from_where(where_filters)" in list_categories_source
    assert "await self._ensure_categories_ready(ctx, store, bootstrap_scope)" in list_categories_source
    assert "bootstrap_scope = concrete_scope_from_where(where_filters)" in retrieve_fn_source
    assert "if retrieve_category and bootstrap_scope is not None:" in retrieve_fn_source
    assert "await self._ensure_categories_ready(ctx, store, bootstrap_scope)" in retrieve_fn_source


def _async_function_source(source: str, name: str) -> str:
    module = ast.parse(source)
    for node in ast.walk(module):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            segment = ast.get_source_segment(source, node)
            assert segment is not None
            return segment
    raise AssertionError(f"async function {name!r} not found")


def _class_node(source: str, name: str) -> ast.ClassDef:
    module = ast.parse(source)
    for node in ast.walk(module):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f"class {name!r} not found")


def _class_assignment(class_node: ast.ClassDef, name: str) -> ast.expr:
    for statement in class_node.body:
        if not isinstance(statement, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in statement.targets):
            return statement.value
    raise AssertionError(f"class assignment {name!r} not found")


def _assignment_call(source: str, target_name: str, call_name: str) -> ast.Call:
    module = ast.parse(source)
    for node in ast.walk(module):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == target_name for target in node.targets):
            continue
        if isinstance(node.value, ast.Call) and getattr(node.value.func, "id", "") == call_name:
            return node.value
    raise AssertionError(f"assignment call {target_name} = {call_name}(...) not found")
