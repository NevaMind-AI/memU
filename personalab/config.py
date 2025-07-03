"""
Configuration module for PersonaLab

Handles environment variables and .env file loading for API keys and settings.
"""

import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv

    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


class Config:
    """Configuration class for PersonaLab settings"""

    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration

        Args:
            env_file: Path to .env file. If None, looks for .env in current directory
        """
        self._load_env_file(env_file)

    def _load_env_file(self, env_file: Optional[str] = None):
        """Load environment variables from .env file"""
        if not DOTENV_AVAILABLE:
            print(
                "Warning: python-dotenv not available. Install with: pip install python-dotenv"
            )
            return

        if env_file:
            env_path = Path(env_file)
        else:
            # Look for .env in current directory and parent directories
            current_path = Path.cwd()
            env_path = None

            for path in [current_path] + list(current_path.parents):
                potential_env = path / ".env"
                if potential_env.exists():
                    env_path = potential_env
                    break

        if env_path and env_path.exists():
            load_dotenv(env_path)
            print(f"Loaded environment variables from: {env_path}")
        else:
            print("No .env file found. Create one from .env.example template")

    # OpenAI Configuration
    @property
    def openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key"""
        return os.getenv("OPENAI_API_KEY")

    @property
    def openai_model(self) -> str:
        """Get OpenAI model name"""
        return os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

    @property
    def openai_base_url(self) -> str:
        """Get OpenAI base URL"""
        return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    # Other LLM Provider Keys
    @property
    def anthropic_api_key(self) -> Optional[str]:
        """Get Anthropic API key"""
        return os.getenv("ANTHROPIC_API_KEY")

    @property
    def azure_openai_api_key(self) -> Optional[str]:
        """Get Azure OpenAI API key"""
        return os.getenv("AZURE_OPENAI_API_KEY")

    @property
    def azure_openai_endpoint(self) -> Optional[str]:
        """Get Azure OpenAI endpoint"""
        return os.getenv("AZURE_OPENAI_ENDPOINT")

    # Pipeline Configuration
    @property
    def default_temperature(self) -> float:
        """Get default temperature for LLM calls"""
        return float(os.getenv("DEFAULT_TEMPERATURE", "0.3"))

    @property
    def default_max_tokens(self) -> int:
        """Get default max tokens for LLM calls"""
        return int(os.getenv("DEFAULT_MAX_TOKENS", "2000"))

    # Debug Settings
    @property
    def log_level(self) -> str:
        """Get log level"""
        return os.getenv("LOG_LEVEL", "INFO")

    @property
    def enable_debug(self) -> bool:
        """Check if debug mode is enabled"""
        return os.getenv("ENABLE_DEBUG", "false").lower() in ("true", "1", "yes")

    def validate_llm_config(self, provider: str = "openai") -> bool:
        """
        Validate that required configuration is available for LLM provider

        Args:
            provider: LLM provider name

        Returns:
            True if configuration is valid
        """
        if provider.lower() == "openai":
            return self.openai_api_key is not None
        elif provider.lower() == "anthropic":
            return self.anthropic_api_key is not None
        elif provider.lower() == "azure":
            return (
                self.azure_openai_api_key is not None
                and self.azure_openai_endpoint is not None
            )

        return False

    def get_llm_config(self, provider: str = "openai") -> dict:
        """
        Get LLM configuration dict for a provider

        Args:
            provider: LLM provider name

        Returns:
            Configuration dict for the provider
        """
        if provider.lower() == "openai":
            config = {
                "api_key": self.openai_api_key,
                "model": self.openai_model,
                "base_url": self.openai_base_url,
                "temperature": self.default_temperature,
                "max_tokens": self.default_max_tokens,
            }
        elif provider.lower() == "anthropic":
            config = {
                "api_key": self.anthropic_api_key,
                "temperature": self.default_temperature,
                "max_tokens": self.default_max_tokens,
            }
        elif provider.lower() == "azure":
            config = {
                "api_key": self.azure_openai_api_key,
                "endpoint": self.azure_openai_endpoint,
                "temperature": self.default_temperature,
                "max_tokens": self.default_max_tokens,
            }
        else:
            config = {
                "temperature": self.default_temperature,
                "max_tokens": self.default_max_tokens,
            }

        # Remove None values
        return {k: v for k, v in config.items() if v is not None}


class LLMConfigManager:
    """
    Unified LLM Configuration Manager
    Centralizes all LLM-related configuration management
    """

    def __init__(self, config: Config):
        """
        Initialize LLM Config Manager

        Args:
            config: Base Config instance
        """
        self.config = config
        self._provider_configs = {}
        self._default_provider = "openai"
        self._init_provider_configs()

    def _init_provider_configs(self):
        """Initialize configurations for all supported providers"""
        # OpenAI Configuration
        self._provider_configs["openai"] = {
            "api_key": self.config.openai_api_key,
            "model": self.config.openai_model,
            "base_url": self.config.openai_base_url,
            "temperature": self.config.default_temperature,
            "max_tokens": self.config.default_max_tokens,
            "provider_type": "openai",
        }

        # Anthropic Configuration
        self._provider_configs["anthropic"] = {
            "api_key": self.config.anthropic_api_key,
            "model": "claude-3-sonnet-20240229",  # Default model
            "temperature": self.config.default_temperature,
            "max_tokens": self.config.default_max_tokens,
            "provider_type": "anthropic",
        }

        # Azure OpenAI Configuration
        self._provider_configs["azure"] = {
            "api_key": self.config.azure_openai_api_key,
            "endpoint": self.config.azure_openai_endpoint,
            "temperature": self.config.default_temperature,
            "max_tokens": self.config.default_max_tokens,
            "provider_type": "azure",
        }

    def get_provider_config(self, provider: str = None) -> dict:
        """
        Get configuration for specified provider

        Args:
            provider: Provider name, defaults to current default

        Returns:
            Provider configuration dict
        """
        if provider is None:
            provider = self._default_provider

        provider = provider.lower()
        if provider not in self._provider_configs:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        config = self._provider_configs[provider].copy()
        # Remove None values
        return {k: v for k, v in config.items() if v is not None}

    def set_default_provider(self, provider: str):
        """
        Set default LLM provider

        Args:
            provider: Provider name
        """
        provider = provider.lower()
        if provider not in self._provider_configs:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        self._default_provider = provider

    def get_default_provider(self) -> str:
        """Get current default provider"""
        return self._default_provider

    def validate_provider(self, provider: str = None) -> bool:
        """
        Validate provider configuration

        Args:
            provider: Provider name, defaults to current default

        Returns:
            True if configuration is valid
        """
        if provider is None:
            provider = self._default_provider

        return self.config.validate_llm_config(provider)

    def get_pipeline_config(self, provider: str = None, **overrides) -> dict:
        """
        Get configuration optimized for pipeline usage

        Args:
            provider: Provider name
            **overrides: Configuration overrides

        Returns:
            Pipeline-optimized configuration
        """
        base_config = self.get_provider_config(provider)

        # Pipeline-specific defaults
        pipeline_defaults = {
            "temperature": 0.3,  # Lower for consistency
            "max_tokens": 2000,
            "timeout": 30,
            "retry_count": 3,
        }

        # Merge: base_config -> pipeline_defaults -> overrides
        result = {**base_config, **pipeline_defaults, **overrides}
        return result

    def list_providers(self) -> list:
        """List all supported providers"""
        return list(self._provider_configs.keys())

    def get_provider_status(self) -> dict:
        """
        Get status of all providers

        Returns:
            Dict with provider status information
        """
        status = {}
        for provider in self._provider_configs.keys():
            status[provider] = {
                "configured": self.validate_provider(provider),
                "config": self.get_provider_config(provider),
            }
        return status


# Global config instance
config = Config()

# Global LLM config manager instance
llm_config_manager = LLMConfigManager(config)


def load_config(env_file: Optional[str] = None) -> Config:
    """
    Load configuration from .env file

    Args:
        env_file: Path to .env file

    Returns:
        Config instance
    """
    global config, llm_config_manager
    config = Config(env_file)
    llm_config_manager = LLMConfigManager(config)
    return config


def get_llm_config_manager() -> LLMConfigManager:
    """
    Get global LLM configuration manager instance

    Returns:
        LLM configuration manager
    """
    return llm_config_manager


def setup_env_file():
    """Helper function to guide users in setting up .env file"""
    env_path = Path(".env")
    example_path = Path(".env.example")

    if env_path.exists():
        print("✓ .env file already exists")
        return

    if example_path.exists():
        print("Setting up .env file from template...")
        example_content = example_path.read_text()
        env_path.write_text(example_content)
        print("✓ Created .env file from .env.example")
        print("📝 Please edit .env file and add your actual API keys")
    else:
        print("❌ .env.example template not found")
        print("💡 Run this to create a basic .env file:")
        print("   echo 'OPENAI_API_KEY=your_api_key_here' > .env")
