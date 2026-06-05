from __future__ import annotations

import ast
from pathlib import Path

from memu.utils.retrieve import normalize_retrieve_method, normalize_retrieve_ranking

ROOT = Path(__file__).resolve().parents[1]


def test_normalize_retrieve_method_uses_config_default() -> None:
    assert normalize_retrieve_method(None, default="llm") == "llm"


def test_normalize_retrieve_method_accepts_case_insensitive_override() -> None:
    assert normalize_retrieve_method(" RAG ", default="llm") == "rag"


def test_normalize_retrieve_method_rejects_unknown_values() -> None:
    try:
        normalize_retrieve_method("hybrid", default="rag")
    except ValueError as exc:
        assert "retrieve method must be 'rag' or 'llm'" in str(exc)
    else:
        raise AssertionError("unknown retrieve method should raise ValueError")


def test_normalize_retrieve_ranking_accepts_case_insensitive_override() -> None:
    assert normalize_retrieve_ranking(" SALIENCE ", default="similarity") == "salience"


def test_normalize_retrieve_ranking_rejects_unknown_values() -> None:
    try:
        normalize_retrieve_ranking("random", default="similarity")
    except ValueError as exc:
        assert "retrieve ranking must be 'similarity' or 'salience'" in str(exc)
    else:
        raise AssertionError("unknown retrieve ranking should raise ValueError")


def test_retrieve_method_override_is_wired_into_retrieve_pipeline() -> None:
    source = (ROOT / "src" / "memu" / "app" / "retrieve.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    retrieve_fn = next(
        node for node in ast.walk(module) if isinstance(node, ast.AsyncFunctionDef) and node.name == "retrieve"
    )
    arg_names = [arg.arg for arg in retrieve_fn.args.args]

    assert "method" in arg_names
    assert "normalize_retrieve_method(method, default=self.retrieve_config.method)" in source
    assert '"retrieve_llm" if retrieve_method == "llm" else "retrieve_rag"' in source
    assert '"method": retrieve_method' in source


def test_retrieve_ranking_override_is_wired_into_rag_item_recall() -> None:
    source = (ROOT / "src" / "memu" / "app" / "retrieve.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    retrieve_fn = next(
        node for node in ast.walk(module) if isinstance(node, ast.AsyncFunctionDef) and node.name == "retrieve"
    )
    arg_names = [arg.arg for arg in retrieve_fn.args.args]
    rag_recall_items = _async_function_source(source, "_rag_recall_items")

    assert "ranking" in arg_names
    assert "normalize_retrieve_ranking(ranking, default=self.retrieve_config.item.ranking)" in source
    assert '"item_ranking": item_ranking' in source
    assert '"item_ranking",' in source
    assert 'ranking=state.get("item_ranking", self.retrieve_config.item.ranking)' in rag_recall_items


def test_rag_retrieve_follows_category_references_with_scope_filters() -> None:
    source = (ROOT / "src" / "memu" / "app" / "retrieve.py").read_text(encoding="utf-8")
    rag_recall_items = _async_function_source(source, "_rag_recall_items")
    merge_hits = _function_source(source, "_merge_referenced_item_hits")

    assert 'getattr(self.retrieve_config.item, "use_category_references", False)' in rag_recall_items
    assert "ref_ids = self._extract_referenced_item_ids(state)" in rag_recall_items
    assert "store.memory_item_repo.list_items_by_ref_ids(ref_ids, where_filters)" in rag_recall_items
    assert "items_pool.update(referenced_items)" in rag_recall_items
    assert "self._merge_referenced_item_hits(" in rag_recall_items
    assert "if item_id not in seen:" in merge_hits


def test_llm_retrieve_respects_category_item_resource_toggles() -> None:
    source = (ROOT / "src" / "memu" / "app" / "retrieve.py").read_text(encoding="utf-8")
    workflow_source = _function_source(source, "_build_llm_retrieve_workflow")
    route_category = _async_function_source(source, "_llm_route_category")
    recall_items = _async_function_source(source, "_llm_recall_items")
    recall_resources = _async_function_source(source, "_llm_recall_resources")

    assert '"retrieve_category", "needs_retrieval", "active_query", "ctx", "store", "where"' in workflow_source
    assert '"retrieve_item",' in workflow_source
    assert '"retrieve_resource",' in workflow_source
    assert 'not state.get("retrieve_category") or not state.get("needs_retrieval")' in route_category
    assert 'not state.get("retrieve_item") or not state.get("needs_retrieval")' in recall_items
    assert 'not state.get("retrieve_resource")' in recall_resources


def test_route_intention_uses_independent_llm_profile() -> None:
    source = (ROOT / "src" / "memu" / "app" / "retrieve.py").read_text(encoding="utf-8")
    rag_workflow = _function_source(source, "_build_rag_retrieve_workflow")
    llm_workflow = _function_source(source, "_build_llm_retrieve_workflow")

    assert "self.retrieve_config.route_intention_llm_profile" in rag_workflow
    assert "self.retrieve_config.route_intention_llm_profile" in llm_workflow
    assert 'config={"chat_llm_profile": self.retrieve_config.sufficiency_check_llm_profile}' not in rag_workflow
    assert 'config={"llm_profile": self.retrieve_config.sufficiency_check_llm_profile}' not in llm_workflow.split(
        'step_id="route_category"',
        1,
    )[0]


def test_direct_retrieve_query_text_is_trimmed_and_rejects_blank_values() -> None:
    source = (ROOT / "src" / "memu" / "app" / "retrieve.py").read_text(encoding="utf-8")
    extract_query_text = _function_source(source, "_extract_query_text")

    assert "text = query.strip()" in extract_query_text
    assert "text = content.strip()" in extract_query_text
    assert "text = content.get(\"text\", \"\")" in extract_query_text
    assert "not isinstance(text, str) or not text.strip()" in extract_query_text
    assert "return text.strip()" in extract_query_text
    assert 'raise ValueError("EMPTY")' in extract_query_text


def test_direct_retrieve_type_hints_accept_string_query_items_without_raw_string_collection() -> None:
    source = (ROOT / "src" / "memu" / "app" / "retrieve.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    retrieve_fn = next(
        node for node in ast.walk(module) if isinstance(node, ast.AsyncFunctionDef) and node.name == "retrieve"
    )
    query_arg = next(arg for arg in retrieve_fn.args.args if arg.arg == "queries")
    retrieve_source = _async_function_source(source, "retrieve")
    format_query_context = _function_source(source, "_format_query_context")
    extract_query_text = _function_source(source, "_extract_query_text")

    assert ast.unparse(query_arg.annotation) == "list[str | Mapping[str, Any]]"
    assert "if not isinstance(queries, list):" in retrieve_source
    assert "queries must be a non-empty list of strings or query objects" in retrieve_source
    assert 'raise ValueError("empty_queries")' not in retrieve_source
    assert "def _format_query_context(self, queries: Sequence[str | Mapping[str, Any]] | None)" in format_query_context
    assert "elif isinstance(q, Mapping):" in format_query_context
    assert "def _extract_query_text(query: str | Mapping[str, Any])" in extract_query_text
    assert "if not isinstance(query, Mapping):" in extract_query_text


def test_direct_retrieve_normalizes_all_query_items_before_workflow() -> None:
    source = (ROOT / "src" / "memu" / "app" / "retrieve.py").read_text(encoding="utf-8")
    retrieve_source = _async_function_source(source, "retrieve")
    normalize_query_item = _function_source(source, "_normalize_query_item")

    assert (
        "normalized_queries = [self._normalize_query_item(query, index=index) for index, query in enumerate(queries)]"
        in retrieve_source
    )
    assert "original_query = self._extract_query_text(normalized_queries[-1])" in retrieve_source
    assert "context_queries_objs: list[dict[str, Any]] = normalized_queries[:-1]" in retrieve_source
    assert '"skip_rewrite": len(normalized_queries) == 1' in retrieve_source
    assert 'return {"role": "user", "content": text}' in normalize_query_item
    assert 'role = query.get("role", "user")' in normalize_query_item
    assert 'normalized_content = {"text": text.strip()}' in normalize_query_item
    assert 'raise ValueError(f"queries[{index}].content.text must be a non-empty string")' in normalize_query_item


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
