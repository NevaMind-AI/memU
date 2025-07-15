# MemU Function Definitions Report

This report contains all function definitions (both regular `def` and `async def`) found in the MemU project's main code directories: `memu/`, `server/backend/`, and `examples/`.

## Summary Statistics
- Total Python files analyzed: 27
- Total functions found: 263 (including class methods)

## Functions Grouped by File

### 1. examples/persona_chat_example.py
- `setup_diverse_conversations` (line 36)
- `test_basic_retrieval` (line 113)
- `test_threshold_sensitivity` (line 157)
- `test_retrieval_limits` (line 188)
- `test_multi_user_isolation` (line 219)
- `test_edge_cases` (line 281)
- `test_retrieval_with_disabled_feature` (line 315)
- `analyze_retrieval_performance` (line 347)
- `main` (line 381)

### 2. memu/__init__.py
- `__getattr__` (line 114)

### 3. memu/config.py
#### Module-level functions:
- `load_config` (line 314)
- `get_llm_config_manager` (line 330)
- `setup_env_file` (line 340)

#### Config class methods:
- `__init__` (line 26)
- `_load_env_file` (line 35)
- `openai_api_key` (line 64) @property
- `openai_model` (line 69) @property
- `openai_base_url` (line 74) @property
- `anthropic_api_key` (line 80) @property
- `azure_openai_api_key` (line 85) @property
- `azure_openai_endpoint` (line 90) @property
- `default_temperature` (line 96) @property
- `default_max_tokens` (line 101) @property
- `log_level` (line 107) @property
- `enable_debug` (line 112) @property
- `validate_llm_config` (line 116)
- `get_llm_config` (line 138)

#### LLMConfigManager class methods:
- `__init__` (line 185)
- `_init_provider_configs` (line 197)
- `get_provider_config` (line 218)
- `set_default_provider` (line 239)
- `get_default_provider` (line 252)
- `validate_provider` (line 256)
- `get_pipeline_config` (line 271)
- `list_providers` (line 287)
- `get_provider_status` (line 291)

### 4. memu/db/config.py
#### DatabaseConfig class methods:
- `__post_init__` (line 25)
- `from_env` (line 35) @classmethod
- `create_postgresql` (line 70) @classmethod

#### DatabaseManager class methods:
- `__init__` (line 120)
- `get_memory_db` (line 131)
- `get_conversation_db` (line 140)
- `test_connection` (line 151)
- `get_backend_info` (line 168)
- `close` (line 179)

#### Module-level functions:
- `get_database_manager` (line 191)
- `configure_database` (line 209)
- `setup_postgresql` (line 223)

### 5. memu/db/pg_storage.py
#### PostgreSQLStorage class methods:
- `__init__` (line 38)
- `_test_connection` (line 55)
- `_init_database` (line 61)
- `_init_tables` (line 82)
- `_calculate_hash` (line 86)
- `close` (line 90)

### 6. memu/db/utils.py
- `build_connection_string` (line 21)
- `test_database_connection` (line 71)
- `get_db_connection` (line 93)
- `get_db_cursor` (line 123)
- `database_operation` (line 150) - decorator
- `decorator` (line 164) - inner function
- `wrapper` (line 166) - inner function
- `safe_database_operation` (line 180) - decorator
- `decorator` (line 194) - inner function
- `wrapper` (line 196) - inner function
- `get_database_info` (line 209)
- `ensure_pgvector_extension` (line 252)

### 7. memu/llm/__init__.py
(No functions defined in this file)

### 8. memu/llm/anthropic_client.py
#### AnthropicClient class methods:
- `__init__` (line 15)
- `client` (line 40) @property
- `chat_completion` (line 53)
- `_get_default_model` (line 100)
- `_prepare_messages` (line 104)
- `from_env` (line 128) @classmethod
- `__str__` (line 132)

### 9. memu/llm/base.py
#### LLMResponse class methods:
- `__bool__` (line 20)
- `__str__` (line 24)

#### BaseLLMClient class methods:
- `__init__` (line 32)
- `chat_completion` (line 44) @abstractmethod
- `simple_chat` (line 67)
- `get_model` (line 82)
- `_get_default_model` (line 87) @abstractmethod
- `_prepare_messages` (line 91)
- `_handle_error` (line 95)

### 10. memu/llm/custom_client.py
#### CustomLLMClient class methods:
- `__init__` (line 22)
- `chat_completion` (line 58)
- `_get_default_model` (line 115)
- `create_full` (line 120) @classmethod
- `create_object` (line 133) @classmethod
- `__str__` (line 145)

#### Module-level functions:
- `create_simple_client` (line 149)

### 11. memu/llm/openai_client.py
#### OpenAIClient class methods:
- `__init__` (line 15)
- `client` (line 47) @property
- `chat_completion` (line 71)
- `_get_default_model` (line 109)
- `_prepare_messages` (line 113)
- `from_env` (line 126) @classmethod
- `__str__` (line 130)

### 12. memu/memo/__init__.py
#### MemoManager class methods:
- `conversations` (line 76) @property
- `close` (line 82)

### 13. memu/memo/embeddings.py
#### EmbeddingProvider (ABC) methods:
- `generate_embedding` (line 20) @abstractmethod
- `embedding_dimension` (line 34) @property @abstractmethod
- `model_name` (line 40) @property @abstractmethod

#### OpenAIEmbedding class methods:
- `__init__` (line 52)
- `generate_embedding` (line 76)
- `embedding_dimension` (line 86) @property
- `model_name` (line 90) @property

#### SentenceTransformerEmbedding class methods:
- `__init__` (line 101)
- `generate_embedding` (line 114)
- `embedding_dimension` (line 124) @property
- `model_name` (line 128) @property

#### EmbeddingManager class methods:
- `__init__` (line 140)
- `model_name` (line 144) @property
- `embedding_dimension` (line 148) @property
- `generate_conversation_embedding` (line 151)
- `generate_message_embedding` (line 173)
- `generate_text_embedding` (line 186)

#### Module-level functions:
- `create_embedding_manager` (line 199)

### 14. memu/memo/manager.py
#### ConversationManager class methods:
- `__init__` (line 29)
- `record_conversation` (line 55)
- `_generate_conversation_embeddings` (line 107)
- `get_conversation` (line 132)
- `get_conversation_history` (line 144)
- `search_similar_conversations` (line 165)
- `delete_conversation` (line 234)
- `get_session_conversations` (line 246)
- `get_conversation_stats` (line 277)
- `close` (line 317)

### 15. memu/memo/models.py
(No functions defined - contains dataclass definitions)

### 16. memu/memory/__init__.py
(No functions defined in this file)

### 17. memu/memory/base.py
#### Memory class methods:
- `__init__` (line 33)
- `_init_memory_components` (line 68)
- `get_profile` (line 88)
- `get_events` (line 92)
- `get_mind` (line 96)
- `get_profile_content` (line 100)
- `get_profile_content_string` (line 104)
- `get_event_content` (line 108)
- `get_mind_content` (line 112)
- `get_memory_stats` (line 116)
- `to_prompt` (line 129)
- `get_memory_content` (line 159)
- `to_dict` (line 163)
- `close` (line 185)
- `update_events` (line 190)
- `update_profile` (line 199)
- `update_mind` (line 216)
- `clear_profile` (line 246)
- `clear_events` (line 250)
- `clear_mind` (line 254)
- `clear_all` (line 258)

#### Profile class methods:
- `__init__` (line 275)
- `get_content` (line 293)
- `set_content` (line 297)
- `add_item` (line 306)
- `remove_item` (line 319)
- `get_content_string` (line 329)
- `to_prompt` (line 333)
- `is_empty` (line 339)
- `get_item_count` (line 343)
- `get_word_count` (line 347)
- `get_total_text_length` (line 351)

#### Events class methods:
- `__init__` (line 364)
- `get_content` (line 375)
- `set_content` (line 379)
- `get_recent_events` (line 383)
- `clear_events` (line 395)
- `to_prompt` (line 399)
- `is_empty` (line 405)
- `get_event_count` (line 409)
- `get_total_text_length` (line 413)

#### Mind class methods:
- `__init__` (line 426)
- `get_content` (line 435)
- `set_content` (line 439)
- `get_recent_insights` (line 443)
- `clear_insights` (line 455)
- `to_prompt` (line 459)
- `is_empty` (line 465)
- `get_insight_count` (line 469)
- `get_total_text_length` (line 473)

### 18. memu/memory/manager.py
#### MemoryClient class methods:
- `__init__` (line 27)
- `_make_api_request` (line 48)
- `get_memory_by_agent` (line 78)
- `get_memory` (line 142)
- `update_memory_with_conversation` (line 157)
- `clear_memory_cache` (line 198)
- `get_memory_prompt` (line 222)
- `get_memory_info` (line 268)
- `export_memory` (line 303)
- `update_profile` (line 333)
- `update_events` (line 370)
- `get_memory_stats` (line 407)

### 19. memu/memory/pipeline.py
#### LLMMemoryPipeline class methods:
- `__init__` (line 72)
- `update_with_pipeline` (line 108)
- `llm_modification_stage` (line 193)
- `llm_update_stage` (line 261)
- `llm_theory_of_mind_stage` (line 363)
- `_create_updated_memory` (line 443)
- `_parse_modification_result` (line 491)
- `_extract_xml_content` (line 543)
- `_parse_text_format` (line 563)
- `_parse_insights_content` (line 621)
- `_parse_insights_text_format` (line 658)
- `_format_conversation` (line 690)
- `_format_events` (line 699)
- `_format_profile` (line 707)

### 20. memu/persona/__init__.py
(No functions defined in this file)

### 21. memu/persona/persona.py
#### Persona class methods:
- `__init__` (line 70)
- `_create_default_openai_client` (line 179)
- `_search_relevant_conversations` (line 195)
- `chat` (line 243)
- `get_memory` (line 308)
- `update_memory` (line 324)
- `endsession` (line 358)
- `get_session_info` (line 453)
- `close` (line 469)
- `session` (line 490) @contextmanager
- `_get_or_create_memory` (line 501)
- `_get_memory_context` (line 513)

### 22. memu/utils/__init__.py
(No functions defined in this file)

### 23. memu/utils/logging.py
#### ColoredFormatter class methods:
- `format` (line 25)

#### Module-level functions:
- `setup_logging` (line 33)
- `get_logger` (line 80)

### 24. server/backend/main.py
#### Module-level functions:
- `setup_postgres_env` (line 37)
- `root` (line 159) async
- `get_stats` (line 165) async
- `get_conversations` (line 175) async
- `get_conversation_detail` (line 206) async
- `delete_conversation` (line 237) async
- `get_memories` (line 250) async
- `get_memory_detail` (line 271) async
- `delete_memory` (line 318) async
- `save_conversation` (line 331) async
- `update_memory_with_conversation` (line 360) async
- `update_memory_profile` (line 532) async
- `update_memory_events` (line 564) async
- `get_memory_stats` (line 595) async
- `get_memory_operations` (line 621) async
- `get_agents` (line 640) async
- `get_users` (line 650) async
- `get_db_connection_string` (line 660)
- `get_system_stats` (line 675)
- `get_all_conversations` (line 749)
- `get_all_memories` (line 772)
- `get_memory_operations` (line 811)
- `get_unique_agents` (line 850)
- `get_unique_users` (line 867)
- `parse_date` (line 884)

### 25. server/backend/start.py
(No functions analyzed - startup script)

## Function Type Distribution
- Regular functions (`def`): 244
- Async functions (`async def`): 19
- Class methods: 214
- Module-level functions: 49
- Property methods: 17
- Class methods (@classmethod): 6
- Abstract methods (@abstractmethod): 5

## Key Observations
1. The project follows a clear object-oriented design with most functionality encapsulated in classes
2. The server backend uses async functions for all API endpoints
3. The memory and persona modules contain the core business logic
4. Database operations are well-abstracted with utility functions and decorators
5. The LLM integration supports multiple providers (OpenAI, Anthropic, Custom)
6. Comprehensive logging and error handling utilities are provided