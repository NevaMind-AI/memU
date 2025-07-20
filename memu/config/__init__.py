"""Configuration module for MemU"""

# Import original config for backward compatibility
import importlib.util
import os

# Import markdown configuration
from .markdown_config import (
    get_config_manager,
    detect_file_type,
    MarkdownConfigManager,
    MarkdownFileConfig,
    # 简化配置API
    get_required_files,
    get_optional_files,
    get_simple_summary,
    get_all_file_configs
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
    # Markdown configuration
    "get_config_manager",
    "detect_file_type",
    "MarkdownConfigManager",
    "MarkdownFileConfig",
    # 简化配置API
    "get_required_files",
    "get_optional_files", 
    "get_simple_summary",
    "get_all_file_configs",
    # LLM configuration (backward compatibility)
    "config",
    "load_config",
    "setup_env_file",
    "LLMConfigManager",
    "get_llm_config_manager",
]
