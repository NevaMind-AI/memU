from __future__ import annotations

from memu.llm import lazyllm_client


def test_lazyllm_client_module_imports_without_optional_dependency() -> None:
    assert lazyllm_client.LazyLLMClient.__name__ == "LazyLLMClient"


def test_lazyllm_missing_dependency_error_is_actionable() -> None:
    if lazyllm_client._LAZYLLM_IMPORT_ERROR is None:
        return

    try:
        lazyllm_client.LazyLLMClient()
    except ImportError as exc:
        message = str(exc)
        assert "memu-py[lazyllm]" in message
        assert "uv sync --extra lazyllm" in message
    else:
        raise AssertionError("missing LazyLLM dependency should raise an actionable ImportError")
