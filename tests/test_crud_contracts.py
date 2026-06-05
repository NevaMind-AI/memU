from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_manual_create_memory_item_passes_source_less_resource_id() -> None:
    for relative_path in ["src/memu/app/crud.py", "src/memu/app/patch.py"]:
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        function_source = _async_function_source(source, "_patch_create_memory_item")
        create_call = _first_method_call(function_source, "create_item")
        keyword_values = {keyword.arg: keyword.value for keyword in create_call.keywords}

        assert "resource_id" in keyword_values, f"{relative_path} must pass resource_id explicitly"
        assert isinstance(keyword_values["resource_id"], ast.Constant)
        assert keyword_values["resource_id"].value is None


def test_memory_item_repo_create_item_accepts_source_less_records() -> None:
    checked_paths = [
        "src/memu/database/repositories/memory_item.py",
        "src/memu/database/inmemory/repositories/memory_item_repo.py",
        "src/memu/database/sqlite/repositories/memory_item_repo.py",
        "src/memu/database/postgres/repositories/memory_item_repo.py",
    ]

    for relative_path in checked_paths:
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        create_fn = _function_node(source, "create_item")
        resource_arg = next(arg for arg in create_fn.args.kwonlyargs if arg.arg == "resource_id")
        resource_default = _kwonly_default(create_fn, "resource_id")

        assert ast.unparse(resource_arg.annotation) == "str | None"
        assert isinstance(resource_default, ast.Constant)
        assert resource_default.value is None


def test_update_memory_item_preserves_categories_when_categories_are_omitted() -> None:
    for relative_path in ["src/memu/app/crud.py", "src/memu/app/patch.py"]:
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        function_source = _async_function_source(source, "_patch_update_memory_item")

        assert 'new_cat_names = memory_payload["categories"]' in function_source
        assert "if new_cat_names is None:" in function_source
        assert "mapped_new_cat_ids = mapped_old_cat_ids" in function_source
        assert "else:" in function_source
        assert "mapped_new_cat_ids = self._map_category_names_to_ids(new_cat_names, ctx)" in function_source


def test_manual_memory_item_inputs_are_normalized_before_workflow() -> None:
    for relative_path in ["src/memu/app/crud.py", "src/memu/app/patch.py"]:
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        create_source = _async_function_source(source, "create_memory_item")
        update_source = _async_function_source(source, "update_memory_item")
        delete_source = _async_function_source(source, "delete_memory_item")
        memory_type_helper = _function_source(source, "_normalize_memory_type")
        categories_helper = _function_source(source, "_normalize_memory_categories")
        string_helper = _function_source(source, "_normalize_non_empty_string")

        assert "memory_type = _normalize_memory_type(memory_type)" in create_source
        assert 'memory_content = _normalize_memory_content(memory_content, field_name="memory_content")' in create_source
        assert (
            'memory_categories = _normalize_memory_categories(memory_categories, field_name="memory_categories")'
            in create_source
        )
        assert "memory_id = _normalize_memory_id(memory_id)" in update_source
        assert "memory_type = _normalize_memory_type(memory_type)" in update_source
        assert "memory_id = _normalize_memory_id(memory_id)" in delete_source
        assert "if memory_content is not None:" in update_source
        assert 'memory_content = _normalize_memory_content(memory_content, field_name="memory_content")' in update_source
        assert "if memory_categories is not None:" in update_source
        assert (
            'memory_categories = _normalize_memory_categories(memory_categories, field_name="memory_categories")'
            in update_source
        )
        assert '_normalize_non_empty_string(value, field_name="memory_type")' in memory_type_helper
        assert "memory_type not in get_args(MemoryType)" in memory_type_helper
        assert "cast(MemoryType, memory_type)" in memory_type_helper
        assert "not isinstance(value, list)" in categories_helper
        assert "not isinstance(value, str) or not value.strip()" in string_helper
        assert "return value.strip()" in string_helper


def test_clear_memory_clears_category_item_relations_before_records() -> None:
    source = (ROOT / "src/memu/app/crud.py").read_text(encoding="utf-8")
    workflow_fn = _function_node(source, "_build_clear_memory_workflow")
    step_ids = _workflow_step_ids(workflow_fn)

    assert "clear_category_item_relations" in step_ids
    assert step_ids.index("clear_category_item_relations") < step_ids.index("clear_memory_categories")
    assert step_ids.index("clear_category_item_relations") < step_ids.index("clear_memory_items")
    assert step_ids.index("clear_category_item_relations") < step_ids.index("clear_memory_resources")

    clear_fn_source = _function_source(source, "_crud_clear_category_item_relations")
    response_fn_source = _function_source(source, "_crud_build_clear_memory_response")

    assert "store.category_item_repo.clear_relations(where_filters)" in clear_fn_source
    assert '"deleted_relations"' in response_fn_source


def test_category_item_repo_contract_exposes_scoped_clear_relations() -> None:
    checked_paths = [
        "src/memu/database/repositories/category_item.py",
        "src/memu/database/inmemory/repositories/category_item_repo.py",
        "src/memu/database/sqlite/repositories/category_item_repo.py",
        "src/memu/database/postgres/repositories/category_item_repo.py",
    ]

    for relative_path in checked_paths:
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        clear_fn = _function_node(source, "clear_relations")
        arg_names = [arg.arg for arg in clear_fn.args.args]

        assert "where" in arg_names
        assert "list[CategoryItem]" in ast.unparse(clear_fn.returns)


def test_delete_memory_item_clears_relations_before_item_delete() -> None:
    for relative_path in ["src/memu/app/crud.py", "src/memu/app/patch.py"]:
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        delete_fn_source = _async_function_source(source, "_patch_delete_memory_item")

        clear_idx = delete_fn_source.index('store.category_item_repo.clear_relations({"item_id": memory_id})')
        delete_idx = delete_fn_source.index("store.memory_item_repo.delete_item(memory_id)")

        assert clear_idx < delete_idx
        assert "get_item_categories(memory_id)" not in delete_fn_source


def test_postgres_delete_item_removes_cache_entry() -> None:
    source = (ROOT / "src/memu/database/postgres/repositories/memory_item_repo.py").read_text(encoding="utf-8")
    delete_fn_source = _function_source(source, "delete_item")

    assert "self.items.pop(item_id, None)" in delete_fn_source


def test_inmemory_scoped_clear_preserves_shared_state_dicts() -> None:
    checked = [
        ("src/memu/database/inmemory/repositories/memory_item_repo.py", "clear_items", "items"),
        ("src/memu/database/inmemory/repositories/resource_repo.py", "clear_resources", "resources"),
        ("src/memu/database/inmemory/repositories/memory_category_repo.py", "clear_categories", "categories"),
    ]

    for relative_path, function_name, attribute_name in checked:
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        function = _function_node(source, function_name)
        function_source = _function_source(source, function_name)

        assert not _assigns_to_self_attribute(function, attribute_name)
        assert f"self.{attribute_name}.pop(" in function_source


def _async_function_source(source: str, name: str) -> str:
    module = ast.parse(source)
    for node in ast.walk(module):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            segment = ast.get_source_segment(source, node)
            assert segment is not None
            return segment
    raise AssertionError(f"async function {name!r} not found")


def _function_source(source: str, name: str) -> str:
    module = ast.parse(source)
    for node in ast.walk(module):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            segment = ast.get_source_segment(source, node)
            assert segment is not None
            return segment
    raise AssertionError(f"function {name!r} not found")


def _function_node(source: str, name: str) -> ast.FunctionDef:
    module = ast.parse(source)
    for node in ast.walk(module):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function {name!r} not found")


def _first_method_call(source: str, method_name: str) -> ast.Call:
    module = ast.parse(source)
    for node in ast.walk(module):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == method_name:
            return node
    raise AssertionError(f"method call {method_name!r} not found")


def _kwonly_default(function: ast.FunctionDef, arg_name: str) -> ast.expr | None:
    for arg, default in zip(function.args.kwonlyargs, function.args.kw_defaults, strict=True):
        if arg.arg == arg_name:
            return default
    raise AssertionError(f"keyword-only argument {arg_name!r} not found")


def _workflow_step_ids(function: ast.FunctionDef) -> list[str]:
    step_ids: list[str] = []

    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Name) and node.func.id == "WorkflowStep":
                for keyword in node.keywords:
                    if keyword.arg == "step_id":
                        assert isinstance(keyword.value, ast.Constant)
                        assert isinstance(keyword.value.value, str)
                        step_ids.append(keyword.value.value)
            self.generic_visit(node)

    Visitor().visit(function)
    return step_ids


def _assigns_to_self_attribute(function: ast.FunctionDef, attribute_name: str) -> bool:
    for node in ast.walk(function):
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets.extend(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets.append(node.target)
        elif isinstance(node, ast.AugAssign):
            targets.append(node.target)

        for target in targets:
            if not isinstance(target, ast.Attribute) or target.attr != attribute_name:
                continue
            if isinstance(target.value, ast.Name) and target.value.id == "self":
                return True
    return False
