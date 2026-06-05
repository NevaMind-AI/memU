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
from memu.server.config import _memory_service_kwargs_from_env, _sqlite_dsn_from_path


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


def test_sqlite_env_path_accepts_full_dsn() -> None:
    assert _sqlite_dsn_from_path("sqlite:///custom.db") == "sqlite:///custom.db"


def test_sqlite_env_path_normalizes_in_memory_alias() -> None:
    assert _sqlite_dsn_from_path(":memory:") == "sqlite:///:memory:"


def test_sqlite_env_path_normalizes_windows_paths() -> None:
    assert _sqlite_dsn_from_path("D:\\memu\\memory.db") == "sqlite:///D:/memu/memory.db"
    assert _sqlite_dsn_from_path("data\\memory.db") == "sqlite:///data/memory.db"


@patch.dict(
    "os.environ",
    {
        "MEMU_DATABASE_PROVIDER": "sqlite",
        "MEMU_SQLITE_PATH": "   ",
    },
    clear=True,
)
def test_server_env_kwargs_blank_sqlite_path_uses_default_file() -> None:
    kwargs = _memory_service_kwargs_from_env()

    assert kwargs["database_config"]["metadata_store"]["dsn"] == "sqlite:///./data/memu.db"


@patch.dict("os.environ", {"MEMU_DATABASE_PROVIDER": "postgres"}, clear=True)
def test_server_env_kwargs_require_postgres_dsn() -> None:
    try:
        _memory_service_kwargs_from_env()
    except ValueError as exc:
        assert "MEMU_DATABASE_DSN is required when MEMU_DATABASE_PROVIDER=postgres" in str(exc)
    else:
        raise AssertionError("Postgres server env config should require MEMU_DATABASE_DSN")


@patch.dict(
    "os.environ",
    {
        "MEMU_DATABASE_PROVIDER": "postgres",
        "MEMU_DATABASE_DSN": " postgresql+psycopg://user:pass@localhost:5432/memu ",
    },
    clear=True,
)
def test_server_env_kwargs_accept_postgres_dsn() -> None:
    kwargs = _memory_service_kwargs_from_env()

    assert kwargs["database_config"]["metadata_store"] == {
        "provider": "postgres",
        "ddl_mode": "create",
        "dsn": "postgresql+psycopg://user:pass@localhost:5432/memu",
    }
    assert "vector_index" not in kwargs["database_config"]


@patch.dict("os.environ", {"MEMU_VECTOR_PROVIDER": " NONE "}, clear=True)
def test_server_env_kwargs_accept_vector_provider_override() -> None:
    kwargs = _memory_service_kwargs_from_env()

    assert kwargs["database_config"]["vector_index"] == {"provider": "none"}


@patch.dict(
    "os.environ",
    {
        "MEMU_DATABASE_PROVIDER": "postgres",
        "MEMU_DATABASE_DSN": " postgresql+psycopg://user:pass@localhost:5432/memu ",
        "MEMU_VECTOR_PROVIDER": " pgvector ",
    },
    clear=True,
)
def test_server_env_kwargs_accept_pgvector_provider_with_postgres_dsn() -> None:
    kwargs = _memory_service_kwargs_from_env()

    assert kwargs["database_config"]["metadata_store"]["dsn"] == "postgresql+psycopg://user:pass@localhost:5432/memu"
    assert kwargs["database_config"]["vector_index"] == {"provider": "pgvector"}


@patch.dict("os.environ", {"MEMU_VECTOR_PROVIDER": "pgvector"}, clear=True)
def test_server_env_kwargs_reject_pgvector_without_postgres_provider() -> None:
    try:
        _memory_service_kwargs_from_env()
    except ValueError as exc:
        assert "MEMU_VECTOR_PROVIDER=pgvector requires MEMU_DATABASE_PROVIDER=postgres" in str(exc)
    else:
        raise AssertionError("pgvector should require the postgres metadata provider")


@patch.dict("os.environ", {"MEMU_VECTOR_PROVIDER": "redis"}, clear=True)
def test_server_env_kwargs_reject_unknown_vector_provider() -> None:
    try:
        _memory_service_kwargs_from_env()
    except ValueError as exc:
        assert "MEMU_VECTOR_PROVIDER must be one of: bruteforce, pgvector, none" in str(exc)
    else:
        raise AssertionError("MEMU_VECTOR_PROVIDER should reject unknown values")


@patch.dict("os.environ", {"MEMU_VECTOR_DSN": "postgresql+psycopg://vectors"}, clear=True)
def test_server_env_kwargs_reject_vector_dsn() -> None:
    try:
        _memory_service_kwargs_from_env()
    except ValueError as exc:
        assert "MEMU_VECTOR_DSN is not supported; pgvector uses MEMU_DATABASE_DSN" in str(exc)
    else:
        raise AssertionError("MEMU_VECTOR_DSN should be rejected until separate vector stores are supported")


@patch.dict(
    "os.environ",
    {
        "MEMU_LLM_PROVIDER": " GROK ",
        "MEMU_LLM_CLIENT_BACKEND": " HTTPX ",
        "MEMU_CHAT_MODEL": " grok-test ",
        "MEMU_EMBED_MODEL": " embed-test ",
        "MEMU_EMBED_BATCH_SIZE": " 8 ",
        "MEMU_DATABASE_PROVIDER": " SQLite ",
        "MEMU_DATABASE_DDL_MODE": " VALIDATE ",
        "MEMU_SQLITE_PATH": " :memory: ",
        "MEMU_RETRIEVE_METHOD": " LLM ",
        "MEMU_RESOURCES_DIR": " ./cache/resources ",
    },
    clear=True,
)
def test_server_env_kwargs_normalize_choices_and_provider_defaults() -> None:
    kwargs = _memory_service_kwargs_from_env()

    llm_profile = kwargs["llm_profiles"]["default"]
    assert llm_profile["provider"] == "grok"
    assert llm_profile["client_backend"] == "httpx"
    assert llm_profile["api_key"] == "XAI_API_KEY"
    assert llm_profile["chat_model"] == "grok-test"
    assert llm_profile["embed_model"] == "embed-test"
    assert llm_profile["embed_batch_size"] == 8
    assert kwargs["database_config"]["metadata_store"] == {
        "provider": "sqlite",
        "ddl_mode": "validate",
        "dsn": "sqlite:///:memory:",
    }
    assert kwargs["retrieve_config"] == {"method": "llm"}
    assert kwargs["blob_config"] == {"resources_dir": "./cache/resources"}


@patch.dict(
    "os.environ",
    {
        "MEMU_API_KEY_ENV": " CUSTOM_API_KEY ",
        "MEMU_DATABASE_PROVIDER": "sqlite",
        "MEMU_DATABASE_DSN": " sqlite:///explicit.db ",
        "MEMU_SQLITE_PATH": "ignored.db",
    },
    clear=True,
)
def test_server_env_kwargs_prefer_explicit_database_dsn() -> None:
    kwargs = _memory_service_kwargs_from_env()

    assert kwargs["llm_profiles"]["default"]["api_key"] == "CUSTOM_API_KEY"
    assert kwargs["database_config"]["metadata_store"]["dsn"] == "sqlite:///explicit.db"


@patch.dict("os.environ", {"MEMU_LLM_CLIENT_BACKEND": "requests"}, clear=True)
def test_server_env_kwargs_reject_unknown_llm_client_backend() -> None:
    try:
        _memory_service_kwargs_from_env()
    except ValueError as exc:
        assert "MEMU_LLM_CLIENT_BACKEND must be one of: httpx, sdk, lazyllm_backend" in str(exc)
    else:
        raise AssertionError("MEMU_LLM_CLIENT_BACKEND should reject unknown values")


@patch.dict("os.environ", {"MEMU_DATABASE_PROVIDER": "mysql"}, clear=True)
def test_server_env_kwargs_reject_unknown_database_provider() -> None:
    try:
        _memory_service_kwargs_from_env()
    except ValueError as exc:
        assert "MEMU_DATABASE_PROVIDER must be one of: inmemory, sqlite, postgres" in str(exc)
    else:
        raise AssertionError("MEMU_DATABASE_PROVIDER should reject unknown values")


@patch.dict("os.environ", {"MEMU_DATABASE_DDL_MODE": "drop"}, clear=True)
def test_server_env_kwargs_reject_unknown_database_ddl_mode() -> None:
    try:
        _memory_service_kwargs_from_env()
    except ValueError as exc:
        assert "MEMU_DATABASE_DDL_MODE must be one of: create, validate" in str(exc)
    else:
        raise AssertionError("MEMU_DATABASE_DDL_MODE should reject unknown values")


@patch.dict("os.environ", {"MEMU_RETRIEVE_METHOD": "hybrid"}, clear=True)
def test_server_env_kwargs_reject_unknown_retrieve_method() -> None:
    try:
        _memory_service_kwargs_from_env()
    except ValueError as exc:
        assert "MEMU_RETRIEVE_METHOD must be one of: rag, llm" in str(exc)
    else:
        raise AssertionError("MEMU_RETRIEVE_METHOD should reject unknown values")


@patch.dict("os.environ", {"MEMU_EMBED_BATCH_SIZE": "0"}, clear=True)
def test_server_env_kwargs_reject_non_positive_embed_batch_size() -> None:
    try:
        _memory_service_kwargs_from_env()
    except ValueError as exc:
        assert "MEMU_EMBED_BATCH_SIZE must be >= 1" in str(exc)
    else:
        raise AssertionError("MEMU_EMBED_BATCH_SIZE should reject non-positive values")
