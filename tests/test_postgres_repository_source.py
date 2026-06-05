from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMORY_ITEM_REPO = ROOT / "src" / "memu" / "database" / "postgres" / "repositories" / "memory_item_repo.py"
MEMORY_CATEGORY_REPO = (
    ROOT / "src" / "memu" / "database" / "postgres" / "repositories" / "memory_category_repo.py"
)
RESOURCE_REPO = ROOT / "src" / "memu" / "database" / "postgres" / "repositories" / "resource_repo.py"


def _function_node(module: ast.Module, name: str) -> ast.FunctionDef:
    for node in ast.walk(module):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing function {name}")


def _calls_method(node: ast.AST, method_name: str) -> bool:
    return any(
        isinstance(child, ast.Call)
        and isinstance(child.func, ast.Attribute)
        and child.func.attr == method_name
        and isinstance(child.func.value, ast.Name)
        and child.func.value.id == "self"
        for child in ast.walk(node)
    )


def test_postgres_local_vector_search_queries_current_items() -> None:
    module = ast.parse(MEMORY_ITEM_REPO.read_text(encoding="utf-8"), filename=str(MEMORY_ITEM_REPO))
    vector_search_fn = _function_node(module, "vector_search_items")
    local_search_fn = _function_node(module, "_vector_search_local")

    assert any(
        isinstance(node, ast.Compare)
        and isinstance(node.left, ast.Name)
        and node.left.id == "top_k"
        and any(isinstance(op, ast.LtE) for op in node.ops)
        for node in ast.walk(vector_search_fn)
    )
    assert _calls_method(vector_search_fn, "_vector_search_local")
    assert _calls_method(local_search_fn, "list_items")


def test_postgres_cascade_delete_paths_prune_relation_cache() -> None:
    item_source = MEMORY_ITEM_REPO.read_text(encoding="utf-8")
    category_source = MEMORY_CATEGORY_REPO.read_text(encoding="utf-8")
    resource_source = RESOURCE_REPO.read_text(encoding="utf-8")

    assert "_drop_relation_cache_for_items(deleted_item_ids)" in item_source
    assert "_drop_relation_cache_for_items({item_id})" in item_source
    assert "rel.item_id not in item_ids" in item_source

    assert "deleted_category_ids = set(deleted)" in category_source
    assert "rel.category_id not in deleted_category_ids" in category_source

    assert "deleted_resource_ids = set(deleted)" in resource_source
    assert "item.resource_id in deleted_resource_ids" in resource_source
    assert "rel.item_id not in deleted_item_ids" in resource_source
