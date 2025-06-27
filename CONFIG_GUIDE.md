# PersonaLab Configuration Guide

This guide explains how to configure PersonaLab with API keys and settings using the `.env` file system.

## Quick Setup

1. **Copy the template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit the .env file:**
   ```bash
   # Open in your favorite editor
   nano .env
   # or
   code .env
   ```

3. **Add your API key:**
   ```env
   OPENAI_API_KEY=sk-your-actual-api-key-here
   ```

4. **Test the configuration:**
   ```bash
   python setup_env.py
   ```

## Automatic Setup

You can also use the setup script:

```bash
python setup_env.py
```

This will:
- Create a `.env` file from the template if it doesn't exist
- Test your configuration
- Show you what needs to be configured

## Configuration Options

### OpenAI Settings

```env
# Required: Your OpenAI API key
OPENAI_API_KEY=sk-your-key-here

# Optional: Model to use (default: gpt-3.5-turbo)
OPENAI_MODEL=gpt-4

# Optional: Custom API base URL
OPENAI_BASE_URL=https://api.openai.com/v1
```

### Pipeline Settings

```env
# Default temperature for LLM calls (0.0-1.0)
DEFAULT_TEMPERATURE=0.3

# Default max tokens for responses
DEFAULT_MAX_TOKENS=2000
```

### Debug Settings

```env
# Logging level
LOG_LEVEL=INFO

# Enable debug mode
ENABLE_DEBUG=false
```

## Using Configuration in Code

### Method 1: Automatic Configuration

```python
from personalab.memory import MemoryUpdatePipeline
from personalab.llm import create_llm_client
from personalab.config import config

# Automatically use .env configuration
if config.validate_llm_config("openai"):
    llm_client = create_llm_client("openai", **config.get_llm_config("openai"))
    pipeline = MemoryUpdatePipeline(llm_client)
else:
    print("Please configure OPENAI_API_KEY in .env file")
```

### Method 2: Manual Configuration

```python
from personalab.config import config

# Get individual settings
api_key = config.openai_api_key
model = config.openai_model
temperature = config.default_temperature

# Check if configuration is valid
if config.validate_llm_config("openai"):
    print("Configuration is ready!")
```

### Method 3: Custom .env File

```python
from personalab.config import load_config

# Load from a specific .env file
custom_config = load_config("path/to/custom.env")
api_key = custom_config.openai_api_key
```

## Examples Usage

All the example files are updated to use the `.env` configuration:

- `example_memory_update.py` - Complete pipeline example
- `simple_memory_example.py` - Basic usage
- `stage_by_stage_example.py` - Individual stages

## Troubleshooting

### "No LLM client provided" Error

This means your API key is not configured. Solutions:

1. **Check if .env file exists:**
   ```bash
   ls -la .env
   ```

2. **Run setup script:**
   ```bash
   python setup_env.py
   ```

3. **Manually check configuration:**
   ```python
   from personalab.config import config
   print(f"API Key configured: {bool(config.openai_api_key)}")
   ```

### "Invalid API key" Error

Your API key is configured but incorrect:

1. **Check your key at:** https://platform.openai.com/account/api-keys
2. **Update .env file** with the correct key
3. **Restart your Python session** to reload the configuration

### Configuration Not Loading

If changes to `.env` aren't taking effect:

1. **Restart Python** - Environment variables are loaded at startup
2. **Check file location** - `.env` should be in your project root
3. **Reload configuration:**
   ```python
   from personalab.config import Config
   config = Config()  # Create fresh instance
   ```

## Security Notes

- **Never commit `.env` files** to version control
- **Use `.env.example`** for templates (without real keys)
- **Keep API keys secure** and rotate them regularly
- **Use environment variables** in production instead of `.env` files

## Environment Variables (Alternative)

Instead of `.env` files, you can set environment variables directly:

```bash
# Linux/Mac
export OPENAI_API_KEY="your-key-here"
python example_memory_update.py

# Windows
set OPENAI_API_KEY=your-key-here
python example_memory_update.py
```

The configuration system will automatically pick up environment variables. 