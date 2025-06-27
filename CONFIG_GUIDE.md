# PersonaLab Configuration Guide

This guide provides comprehensive configuration instructions for PersonaLab, including LLM provider setup, memory configuration, and system customization.

## Table of Contents

1. [Quick Start Configuration](#quick-start-configuration)
2. [LLM Provider Configuration](#llm-provider-configuration)
3. [Memory System Configuration](#memory-system-configuration)
4. [Database Configuration](#database-configuration)
5. [Pipeline Configuration](#pipeline-configuration)
6. [Advanced Configuration](#advanced-configuration)
7. [Environment Variables](#environment-variables)
8. [Configuration Examples](#configuration-examples)

## Quick Start Configuration

For basic usage, PersonaLab can be configured with minimal setup:

```python
from personalab.main import Memory

# Basic configuration with auto-detected LLM
memory = Memory("my_agent", enable_llm_search=True)
```

For the new unified architecture:

```python
from personalab.memory import MemoryManager

# Quick setup with auto-configuration
memory_manager = MemoryManager()
```

## LLM Provider Configuration

### Auto-Detection Setup

PersonaLab can automatically detect and configure available LLM providers:

```python
from personalab.llm import LLMManager

# Automatically detect available providers
llm_manager = LLMManager.create_quick_setup()

# Use with memory system
memory = Memory("agent_id", llm_instance=llm_manager.get_current_provider())
```

### Manual Provider Configuration

#### OpenAI Configuration

```python
from personalab.llm import OpenAILLM

# Basic OpenAI setup
openai_llm = OpenAILLM(
    api_key="your-openai-api-key",
    model="gpt-4",
    temperature=0.3,
    max_tokens=2000
)

# Use with memory system
memory = Memory("agent_id", llm_instance=openai_llm)
```

Environment variables for OpenAI:
```bash
export OPENAI_API_KEY="your-openai-api-key"
export OPENAI_MODEL="gpt-4"
export OPENAI_TEMPERATURE="0.3"
```

#### Anthropic Claude Configuration

```python
from personalab.llm import AnthropicLLM

# Anthropic Claude setup
claude_llm = AnthropicLLM(
    api_key="your-anthropic-api-key",
    model="claude-3-sonnet-20240229",
    temperature=0.3,
    max_tokens=2000
)
```

Environment variables for Anthropic:
```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export ANTHROPIC_MODEL="claude-3-sonnet-20240229"
```

#### Google Gemini Configuration

```python
from personalab.llm import GeminiLLM

# Google Gemini setup
gemini_llm = GeminiLLM(
    api_key="your-google-api-key",
    model="gemini-pro",
    temperature=0.3
)
```

Environment variables for Google Gemini:
```bash
export GOOGLE_API_KEY="your-google-api-key"
export GOOGLE_MODEL="gemini-pro"
```

#### Azure OpenAI Configuration

```python
from personalab.llm import AzureOpenAILLM

# Azure OpenAI setup
azure_llm = AzureOpenAILLM(
    api_key="your-azure-api-key",
    azure_endpoint="https://your-resource.openai.azure.com/",
    api_version="2023-05-15",
    deployment_name="your-deployment-name"
)
```

Environment variables for Azure OpenAI:
```bash
export AZURE_OPENAI_KEY="your-azure-api-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_VERSION="2023-05-15"
export AZURE_OPENAI_DEPLOYMENT="your-deployment-name"
```

#### Multiple Provider Setup

```python
from personalab.llm import LLMManager

# Configure multiple providers
llm_manager = LLMManager()

# Add multiple providers
llm_manager.add_provider("openai", openai_llm)
llm_manager.add_provider("claude", claude_llm)
llm_manager.add_provider("gemini", gemini_llm)

# Switch between providers
llm_manager.switch_provider("claude")
current_llm = llm_manager.get_current_provider()
```

## Memory System Configuration

### Basic Memory Configuration

```python
from personalab.main import Memory

# Configure memory with custom settings
memory = Memory(
    agent_id="my_agent",
    enable_deep_search=True,
    enable_llm_search=True,
    llm_instance=your_llm_instance
)
```

### Unified Memory Manager Configuration

```python
from personalab.memory import MemoryManager

# Advanced memory manager configuration
memory_manager = MemoryManager(
    db_path="custom_memory.db",
    llm_client=your_llm_client,
    # LLM configuration
    temperature=0.3,
    max_tokens=2000,
    # Pipeline configuration
    enable_tom_analysis=True,
    tom_confidence_threshold=0.7
)
```

### Memory Component Configuration

```python
from personalab.memory import Memory

# Create memory with specific configuration
memory = Memory(agent_id="agent_123")

# Configure profile memory
memory.profile_memory.update_content("Initial profile information")

# Configure event memory with custom capacity
memory.event_memory.max_events = 100

# Configure ToM memory with custom capacity
memory.tom_memory.max_insights = 50
```

## Database Configuration

### SQLite Configuration (Default)

```python
from personalab.memory import MemoryManager

# Default SQLite configuration
memory_manager = MemoryManager(db_path="memory.db")

# Custom SQLite path
memory_manager = MemoryManager(db_path="/path/to/custom/memory.db")
```

### Database Connection Settings

```python
from personalab.memory.storage import MemoryRepository

# Custom database configuration
repository = MemoryRepository(
    db_path="memory.db",
    # Connection settings
    connection_timeout=30,
    max_connections=10,
    # Performance settings
    enable_wal_mode=True,
    enable_foreign_keys=True
)
```

## Pipeline Configuration

### Basic Pipeline Configuration

```python
from personalab.memory.pipeline import MemoryUpdatePipeline

# Configure update pipeline
pipeline = MemoryUpdatePipeline(
    llm_client=your_llm_client,
    # LLM settings for pipeline
    temperature=0.3,
    max_tokens=2000,
    # Pipeline-specific settings
    enable_modification_stage=True,
    enable_update_stage=True,
    enable_tom_stage=True
)
```

### Stage-Specific Configuration

```python
# Configure individual pipeline stages
pipeline_config = {
    # Modification stage
    "modification": {
        "temperature": 0.2,
        "max_tokens": 1000,
        "enable_safety_check": True
    },
    # Update stage
    "update": {
        "temperature": 0.3,
        "max_tokens": 1500,
        "profile_update_threshold": 0.6
    },
    # Theory of Mind stage
    "tom": {
        "temperature": 0.4,
        "max_tokens": 2000,
        "confidence_threshold": 0.7,
        "enable_psychological_analysis": True
    }
}

pipeline = MemoryUpdatePipeline(
    llm_client=your_llm_client,
    **pipeline_config
)
```

## Advanced Configuration

### Search Configuration

```python
# Configure search parameters
search_config = {
    "enable_semantic_search": True,
    "similarity_threshold": 60.0,
    "max_search_results": 15,
    "enable_llm_ranking": True,
    "search_timeout": 30
}

memory = Memory(
    agent_id="agent_id",
    **search_config
)
```

### Performance Configuration

```python
# Performance optimization settings
performance_config = {
    "enable_memory_cache": True,
    "cache_size": 1000,
    "enable_lazy_loading": True,
    "batch_size": 50,
    "enable_async_processing": False
}

memory_manager = MemoryManager(
    **performance_config
)
```

### Logging Configuration

```python
import logging
from personalab.config import setup_logging

# Configure logging
setup_logging(
    level=logging.INFO,
    log_file="personalab.log",
    enable_console_output=True,
    enable_file_output=True,
    log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
```

## Environment Variables

PersonaLab supports configuration through environment variables:

### Core Settings
```bash
# Database configuration
export PERSONALAB_DB_PATH="memory.db"
export PERSONALAB_DB_TIMEOUT="30"

# Performance settings
export PERSONALAB_CACHE_SIZE="1000"
export PERSONALAB_BATCH_SIZE="50"

# Pipeline settings
export PERSONALAB_ENABLE_TOM="true"
export PERSONALAB_TOM_THRESHOLD="0.7"
```

### LLM Provider Settings
```bash
# OpenAI
export OPENAI_API_KEY="your-key"
export OPENAI_MODEL="gpt-4"
export OPENAI_TEMPERATURE="0.3"

# Anthropic
export ANTHROPIC_API_KEY="your-key"
export ANTHROPIC_MODEL="claude-3-sonnet-20240229"

# Google
export GOOGLE_API_KEY="your-key"
export GOOGLE_MODEL="gemini-pro"

# Azure OpenAI
export AZURE_OPENAI_KEY="your-key"
export AZURE_OPENAI_ENDPOINT="your-endpoint"
export AZURE_OPENAI_VERSION="2023-05-15"
export AZURE_OPENAI_DEPLOYMENT="your-deployment"
```

### Security Settings
```bash
# Security configuration
export PERSONALAB_ENABLE_ENCRYPTION="true"
export PERSONALAB_ENCRYPTION_KEY="your-encryption-key"
export PERSONALAB_ENABLE_AUDIT_LOG="true"
```

## Configuration Examples

### Example 1: Basic AI Chatbot

```python
from personalab.main import Memory
from personalab.llm import LLMManager

# Setup for basic chatbot
llm_manager = LLMManager.create_quick_setup()
memory = Memory(
    agent_id="chatbot_v1",
    enable_llm_search=True,
    llm_instance=llm_manager.get_current_provider()
)

# Use in chatbot
def process_message(user_message):
    # Check if search is needed
    if memory.need_search(user_message):
        search_results = memory.deep_search(user_message)
        context = search_results.get('relevant_context', '')
    else:
        context = ""
    
    # Update memory with conversation
    conversation = f"User: {user_message}\nBot: [response will be here]"
    memory.update_agent_profile_memory(conversation)
    
    return context
```

### Example 2: Advanced Multi-Agent System

```python
from personalab.memory import MemoryManager
from personalab.llm import LLMManager

# Setup for multi-agent system
llm_manager = LLMManager()
llm_manager.add_provider("openai", openai_llm)
llm_manager.add_provider("claude", claude_llm)

memory_manager = MemoryManager(
    db_path="multi_agent_memory.db",
    llm_client=llm_manager.get_current_provider(),
    temperature=0.3,
    max_tokens=2000
)

# Manage multiple agents
agents = ["agent_researcher", "agent_writer", "agent_reviewer"]

for agent_id in agents:
    memory = memory_manager.get_or_create_memory(agent_id)
    
    # Configure agent-specific profiles
    if agent_id == "agent_researcher":
        memory.update_profile("I am a research specialist focused on data analysis")
    elif agent_id == "agent_writer":
        memory.update_profile("I am a creative writer specializing in content creation")
    elif agent_id == "agent_reviewer":
        memory.update_profile("I am a quality reviewer ensuring accuracy and clarity")
```

### Example 3: Production System Configuration

```python
import os
from personalab.memory import MemoryManager
from personalab.llm import LLMManager
from personalab.config import ProductionConfig

# Production configuration
config = ProductionConfig(
    # Database settings
    db_path=os.getenv("PERSONALAB_DB_PATH", "production_memory.db"),
    enable_backup=True,
    backup_interval=3600,  # 1 hour
    
    # Performance settings
    enable_caching=True,
    cache_size=5000,
    enable_connection_pooling=True,
    max_connections=50,
    
    # Security settings
    enable_encryption=True,
    enable_audit_logging=True,
    enable_rate_limiting=True,
    
    # Monitoring settings
    enable_metrics=True,
    metrics_port=8080,
    enable_health_checks=True
)

# Initialize with production config
memory_manager = MemoryManager.from_config(config)
```

## Configuration Validation

PersonaLab provides configuration validation to ensure proper setup:

```python
from personalab.config import validate_config, ConfigValidationError

try:
    # Validate configuration
    validate_config({
        "llm_provider": "openai",
        "api_key": "your-key",
        "model": "gpt-4",
        "database_path": "memory.db"
    })
    print("Configuration is valid")
except ConfigValidationError as e:
    print(f"Configuration error: {e}")
```

## Troubleshooting Configuration Issues

### Common Issues and Solutions

1. **LLM Provider Not Available**
   ```python
   # Check available providers
   from personalab.llm import list_available_providers
   providers = list_available_providers()
   print(f"Available providers: {providers}")
   ```

2. **Database Connection Issues**
   ```python
   # Test database connection
   from personalab.memory.storage import test_database_connection
   success = test_database_connection("memory.db")
   if not success:
       print("Database connection failed")
   ```

3. **Memory Configuration Issues**
   ```python
   # Validate memory configuration
   from personalab.memory import validate_memory_config
   is_valid = validate_memory_config(your_config)
   ```

For additional support and configuration assistance, please refer to the [GitHub Issues](https://github.com/NevaMind-AI/PersonaLab/issues) or our [documentation](https://docs.nevamind.ai). 