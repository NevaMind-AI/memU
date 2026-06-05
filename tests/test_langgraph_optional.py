from __future__ import annotations

from pydantic import ValidationError

from memu.integrations import langgraph


def test_langgraph_module_imports_without_optional_dependencies() -> None:
    assert langgraph.MemULangGraphTools.__name__ == "MemULangGraphTools"


def test_langgraph_missing_dependency_error_is_actionable() -> None:
    if langgraph._LANGGRAPH_IMPORT_ERROR is None:
        return

    try:
        langgraph.MemULangGraphTools(object())
    except ImportError as exc:
        message = str(exc)
        assert "memu-py[langgraph]" in message
        assert "uv sync --extra langgraph" in message
    else:
        raise AssertionError("missing LangGraph dependencies should raise an actionable ImportError")


def test_langgraph_scope_keeps_explicit_user_id_authoritative() -> None:
    metadata = {"user_id": "metadata-user", "team_id": "team1"}

    scope = langgraph._scope_with_user(" explicit-user ", metadata)

    assert scope == {"user_id": "explicit-user", "team_id": "team1"}
    assert metadata == {"user_id": "metadata-user", "team_id": "team1"}


def test_langgraph_input_schemas_trim_and_validate_bounds() -> None:
    save_input = langgraph.SaveRecallInput(content=" remember this ", user_id=" user1 ")
    search_input = langgraph.SearchRecallInput(query=" what changed? ", user_id=" user1 ", limit=3)

    assert save_input.content == "remember this"
    assert save_input.user_id == "user1"
    assert search_input.query == "what changed?"
    assert search_input.user_id == "user1"
    assert search_input.limit == 3

    for kwargs in (
        {"query": "", "user_id": "user1"},
        {"query": "x", "user_id": ""},
        {"query": "x", "user_id": "user1", "limit": 0},
        {"query": "x", "user_id": "user1", "min_relevance_score": 1.1},
    ):
        try:
            langgraph.SearchRecallInput(**kwargs)
        except ValidationError:
            pass
        else:
            raise AssertionError(f"SearchRecallInput should reject invalid values: {kwargs}")
