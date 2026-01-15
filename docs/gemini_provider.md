# Gemini Provider Integration

MemU supports Google's Gemini models via the OpenAI-compatible API provided by Google.

## Configuration

To use Gemini, you need to configure your LLM profile in `config.yaml` or when initializing `MemoryService`.

### Prerequisites

1.  Obtain an API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2.  Set the `GEMINI_API_KEY` environment variable.

```bash
export GEMINI_API_KEY="your-gemini-api-key"
```

### Usage

You can switch the provider to `gemini` in your configuration.

#### In Python Code

```python
from memu.app import MemoryService

service = MemoryService(
    llm_profiles={
        "default": {
            "provider": "gemini",
            "api_key": "your-gemini-api-key",  # Optional if env var is set
            "chat_model": "gemini-2.0-flash-exp",
            "embed_model": "text-embedding-004",
        }
    }
)
```

#### Default Defaults
If you specify `provider="gemini"`, the following defaults are applied automatically if not overridden:
-   **Base URL**: `https://generativelanguage.googleapis.com/v1beta/openai/`
-   **Chat Model**: `gemini-2.0-flash-exp`
-   **Embed Model**: `text-embedding-004`

## Features Supported

-   **Text Generation**: Full chat completion support.
-   **Vision**: Multi-modal inputs (images) are supported via the standard OpenAI vision format.
-   **Embeddings**: Text embeddings using Gemini's embedding models.
