"""
Server Configuration

Environment-based configuration for the MemU self-hosted server.
"""

import os
from functools import lru_cache
from typing import List, Optional, Union

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Server settings from environment variables"""
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # CORS settings
    cors_origins: Union[str, List[str]] = "*"  # Will be converted to list in __init__
    
    # Memory settings
    memory_dir: str = "memu/server/memory"
    enable_embeddings: bool = True
    
    # LLM settings
    llm_provider: str = "openai"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    
    # Anthropic settings
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-sonnet-20240229"
    
    # DeepSeek settings
    deepseek_api_key: Optional[str] = None
    deepseek_model: str = "deepseek-chat"
    
    # Task queue settings (for future Celery integration)
    enable_task_queue: bool = False
    redis_url: str = "redis://localhost:6379/0"
    
    # Authentication settings (for future implementation)
    require_auth: bool = False
    secret_key: str = "dev-secret-key"
    
    model_config = {
        "env_file": ".env",
        "env_prefix": "MEMU_",
        "case_sensitive": False,
        "extra": "ignore"
    }
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Handle special environment variables that don't follow the prefix pattern
        import os
        if not self.openai_api_key:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.anthropic_api_key:
            self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.deepseek_api_key:
            self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        
        # Parse CORS origins if provided as comma-separated string
        if isinstance(self.cors_origins, str):
            if self.cors_origins == "*":
                self.cors_origins = ["*"]
            else:
                self.cors_origins = [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
