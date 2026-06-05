from __future__ import annotations

from unittest.mock import patch

from pydantic import ValidationError

from memu.app.settings import (
    CategoryConfig,
    DatabaseConfig,
    LLMConfig,
    LLMProfilesConfig,
    MemorizeConfig,
    RetrieveConfig,
    default_api_key_env,
    resolve_api_key,
)


@patch.dict("os.environ", {"OPENAI_API_KEY": "resolved-openai-key"})
def test_resolve_api_key_environment_variable_names() -> None:
    assert resolve_api_key("OPENAI_API_KEY") == "resolved-openai-key"


@patch.dict("os.environ", {"OPENAI_API_KEY": " resolved-openai-key "})
def test_resolve_api_key_trims_environment_variable_values() -> None:
    assert resolve_api_key("OPENAI_API_KEY") == "resolved-openai-key"


@patch.dict("os.environ", {"OPENAI_API_KEY": "resolved-openai-key"})
def test_resolve_api_key_preserves_literal_api_keys() -> None:
    assert resolve_api_key("sk-literal-key") == "sk-literal-key"


def test_resolve_api_key_normalizes_missing_api_key_to_empty_string() -> None:
    assert resolve_api_key(None) == ""


def test_default_api_key_env_matches_provider_defaults() -> None:
    assert default_api_key_env("openai") == "OPENAI_API_KEY"
    assert default_api_key_env(" GROK ") == "XAI_API_KEY"


def test_llm_config_normalizes_provider_before_defaults() -> None:
    config = LLMConfig(provider=" GROK ")

    assert config.provider == "grok"
    assert config.base_url == "https://api.x.ai/v1"
    assert config.api_key == "XAI_API_KEY"
    assert config.chat_model == "grok-2-latest"


def test_llm_config_normalizes_client_backend() -> None:
    config = LLMConfig(client_backend=" HTTPX ")

    assert config.client_backend == "httpx"


def test_llm_config_rejects_unknown_client_backend() -> None:
    try:
        LLMConfig(client_backend="http")
    except ValidationError as exc:
        assert "client_backend" in str(exc)
    else:
        raise AssertionError("LLMConfig should reject unknown client_backend values")


def test_llm_config_rejects_non_positive_embed_batch_size() -> None:
    try:
        LLMConfig(embed_batch_size=0)
    except ValidationError as exc:
        assert "embed_batch_size" in str(exc)
    else:
        raise AssertionError("LLMConfig should reject non-positive embed_batch_size")


def test_retrieve_numeric_bounds_reject_invalid_values() -> None:
    invalid_configs = [
        {"category": {"top_k": 0}},
        {"item": {"top_k": 0}},
        {"item": {"recency_decay_days": 0}},
        {"resource": {"top_k": 0}},
    ]

    for config in invalid_configs:
        try:
            RetrieveConfig(**config)
        except ValidationError:
            pass
        else:
            raise AssertionError(f"RetrieveConfig should reject invalid numeric bounds: {config}")


def test_memorize_numeric_bounds_reject_invalid_values() -> None:
    invalid_configs = [
        {"category_assign_threshold": -0.01},
        {"category_assign_threshold": 1.01},
        {"default_category_summary_target_length": 0},
    ]

    for config in invalid_configs:
        try:
            MemorizeConfig(**config)
        except ValidationError:
            pass
        else:
            raise AssertionError(f"MemorizeConfig should reject invalid numeric bounds: {config}")

    try:
        CategoryConfig(name="facts", target_length=0)
    except ValidationError:
        pass
    else:
        raise AssertionError("CategoryConfig should reject non-positive target_length")


def test_database_config_allows_sqlite_without_explicit_dsn() -> None:
    config = DatabaseConfig(metadata_store={"provider": "sqlite"})

    assert config.metadata_store.dsn is None
    assert config.vector_index is not None
    assert config.vector_index.provider == "bruteforce"


def test_retrieve_config_has_independent_route_intention_profile() -> None:
    config = RetrieveConfig(route_intention_llm_profile="router", sufficiency_check_llm_profile="judge")

    assert config.route_intention_llm_profile == "router"
    assert config.sufficiency_check_llm_profile == "judge"


def test_workflow_profile_names_are_trimmed_and_reject_blank_values() -> None:
    retrieve_config = RetrieveConfig(
        route_intention_llm_profile=" router ",
        sufficiency_check_llm_profile=" judge ",
        llm_ranking_llm_profile=" ranker ",
    )
    memorize_config = MemorizeConfig(
        preprocess_llm_profile=" preprocess ",
        memory_extract_llm_profile=" extract ",
        category_update_llm_profile=" summarize ",
    )

    assert retrieve_config.route_intention_llm_profile == "router"
    assert retrieve_config.sufficiency_check_llm_profile == "judge"
    assert retrieve_config.llm_ranking_llm_profile == "ranker"
    assert memorize_config.preprocess_llm_profile == "preprocess"
    assert memorize_config.memory_extract_llm_profile == "extract"
    assert memorize_config.category_update_llm_profile == "summarize"

    try:
        RetrieveConfig(route_intention_llm_profile=" ")
    except ValidationError as exc:
        assert "route_intention_llm_profile" in str(exc)
    else:
        raise AssertionError("RetrieveConfig should reject blank route_intention_llm_profile")


def test_llm_profile_names_are_trimmed_in_profile_map_keys() -> None:
    config = LLMProfilesConfig.model_validate({" default ": {"api_key": "A"}})

    assert "default" in config.profiles
    assert config.profiles["default"].api_key == "A"
    assert "embedding" in config.profiles
