"""Shared extraction validation accepts useful output independently of length."""

import pytest

from memu.hosts.query_extraction import select_query, validate_query


@pytest.mark.parametrize("query", ["Windows task cleanup", "中" * 201, "topic " * 400])
def test_extracted_query_is_retained_without_length_rejection(query):
    trace: dict[str, object] = {}
    selected = select_query("background " * 250, trace, lambda _: validate_query({"query": f"  {query}  "}))
    assert selected == query.strip()
    assert trace["query_source"] == "extracted"
    assert trace["extraction_status"] == "succeeded"


@pytest.mark.parametrize("value", [None, [], {}, {"query": None}, {"query": 3}, {"query": " \t\n"}])
def test_invalid_extracted_query_is_rejected(value):
    with pytest.raises(ValueError, match="Invalid extracted query"):
        validate_query(value)
