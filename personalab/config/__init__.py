"""Configuration module for PersonaLab"""

# Import database configuration functions
# Import original config for backward compatibility
import importlib.util
import os

from .database import (
    DatabaseConfig,
    DatabaseManager,
    get_database_manager,
    setup_postgresql,
)

_config_file_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config.py"
)
_config_spec = importlib.util.spec_from_file_location(
    "personalab_config", _config_file_path
)
_config_module = importlib.util.module_from_spec(_config_spec)
_config_spec.loader.exec_module(_config_module)

# Export config objects
config = _config_module.config
load_config = _config_module.load_config
setup_env_file = _config_module.setup_env_file
LLMConfigManager = _config_module.LLMConfigManager
get_llm_config_manager = _config_module.get_llm_config_manager

__all__ = [
    # Database configuration
    "DatabaseConfig",
    "DatabaseManager",
    "setup_postgresql",
    "get_database_manager",
    # LLM configuration (backward compatibility)
    "config",
    "load_config",
    "setup_env_file",
    "LLMConfigManager",
    "get_llm_config_manager",
]
