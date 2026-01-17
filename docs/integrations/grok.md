# Grok (xAI) Integration

MemU supports **Grok**, the AI model from xAI, as a first-class LLM provider.

## Prerequisites

1.  **xAI Account:** You need an active account with [xAI](https://x.ai/).
2.  **API Key:** Obtain an API key from the [xAI Console](https://console.x.ai/).

## Configuration

To enable Grok, you need to set the `XAI_API_KEY` environment variable.

### Environment Variable

```bash
export XAI_API_KEY="your-xai-api-key-here"
```

PowerShell:

```powershell
$env:XAI_API_KEY="your-xai-api-key-here"
```

## Usage

To use Grok as your LLM provider, switch the `provider` setting to `grok`. This can be done in your configuration file or when initializing the application.

### Python Example

```python
from memu.app.settings import LLMConfig

# Configure MemU to use Grok
config = LLMConfig(
    provider="grok",
    # The default API key env var is XAI_API_KEY
    # The default model is grok-2-latest
)

print(f"Using provider: {config.provider}")
print(f"Base URL: {config.base_url}")
print(f"Chat Model: {config.chat_model}")
```

## Models Supported

We currently support the following Grok models:

*   **grok-2-latest** (Default)

The integration automatically sets the base URL to `https://api.x.ai/v1`.
