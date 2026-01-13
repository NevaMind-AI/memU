# Claude Model Provider

This document describes how to use Anthropic's Claude as an LLM provider in MemU.

## Overview

MemU supports Claude as an alternative to OpenAI for LLM operations. Claude integration provides:

- Chat completions for memory summarization and extraction
- Vision capabilities for image understanding
- Compatible with Claude 3.5 Sonnet, Claude 3 Opus, and other Claude models

## Requirements

### Dependencies

Install the Anthropic SDK:

```bash
pip install anthropic
```

### API Key

Get your API key from [Anthropic Console](https://console.anthropic.com/).

Set the environment variable:

```bash
export ANTHROPIC_API_KEY=your-api-key
```

Since Claude doesn't have native embeddings, you'll also need an OpenAI key for embeddings:

```bash
export OPENAI_API_KEY=your-openai-key
```

## Configuration

### Using LLMConfig

Configure MemU to use Claude by setting the provider:

```python
from memu.app.settings import LLMConfig

llm_config = LLMConfig(
    provider="claude",
    base_url="https://api.anthropic.com",
    api_key="your-anthropic-api-key",  # Or use ANTHROPIC_API_KEY env var
    chat_model="claude-opus-4-5-20251124",
)
```

### Available Models

| Model | Description | Best For |
|-------|-------------|----------|
| `claude-opus-4-5-20251124` | Claude Opus 4.5 - most intelligent | Complex coding, agents, enterprise |
| `claude-opus-4-5-20251124` | Claude 4 Opus | Complex reasoning, agents |
| `claude-opus-4-1-20250414` | Claude Opus 4.1 | Agentic tasks, coding |
| `claude-sonnet-4-5-20250929` | Claude Sonnet 4.5 | Balanced speed/capability |
| `claude-sonnet-4-20250514` | Claude 4 Sonnet | Good balance |
| `claude-haiku-4-5-20251015` | Claude Haiku 4.5 | Fast, efficient |
| `claude-3-5-sonnet-20241022` | Claude 3.5 Sonnet | Legacy, fast |

## Usage

### With MemoryService

```python
from memu import MemoryService
from memu.app.settings import LLMConfig, LLMProfilesConfig

# Configure Claude as the LLM provider
llm_profiles = LLMProfilesConfig({
    "default": LLMConfig(
        provider="claude",
        base_url="https://api.anthropic.com",
        api_key="your-api-key",
        chat_model="claude-opus-4-5-20251124",
    ),
    # Use OpenAI for embeddings (Claude doesn't have embedding API)
    "embedding": LLMConfig(
        provider="openai",
        base_url="https://api.openai.com/v1",
        api_key="your-openai-key",
        embed_model="text-embedding-3-small",
    ),
})

service = MemoryService(llm_profiles=llm_profiles)
```

### Direct SDK Client Usage

```python
from memu.llm.claude_sdk import ClaudeSDKClient

client = ClaudeSDKClient(
    api_key="your-api-key",
    chat_model="claude-opus-4-5-20251124",
)

# Summarize text
summary, response = await client.summarize(
    "Long text to summarize...",
    system_prompt="Be concise and focus on key points.",
    max_tokens=500,
)

# Vision (describe an image)
description, response = await client.vision(
    prompt="Describe what you see in this image",
    image_path="./image.jpg",
    system_prompt="Be detailed and accurate.",
)
```

### HTTP Client Usage

```python
from memu.llm.http_client import HTTPLLMClient

client = HTTPLLMClient(
    base_url="https://api.anthropic.com",
    api_key="your-api-key",
    chat_model="claude-opus-4-5-20251124",
    provider="claude",
)

# Summarize
summary, raw_response = await client.summarize(
    "Text to summarize",
    system_prompt="Summarize in one paragraph.",
)
```

## Running the Example

A complete runnable example is provided:

```bash
export ANTHROPIC_API_KEY=your-anthropic-key
export OPENAI_API_KEY=your-openai-key  # For embeddings
python examples/example_claude_provider.py
```

This example tests:
- Direct SDK client usage (summarization)
- HTTP client usage
- Full memorization workflow
- Memory retrieval

## Limitations

### No Native Embeddings

Claude does not have a native embedding API. For embeddings, use a separate provider:

- **OpenAI**: `text-embedding-3-small` or `text-embedding-3-large`
- **Voyage AI**: Anthropic's recommended embedding partner
- **Cohere**: `embed-english-v3.0` or `embed-multilingual-v3.0`

Example configuration with separate embedding provider:

```python
llm_profiles = LLMProfilesConfig({
    "default": LLMConfig(
        provider="claude",
        api_key="anthropic-key",
        chat_model="claude-sonnet-4-20250514",
    ),
    "embedding": LLMConfig(
        provider="openai",
        api_key="openai-key",
        embed_model="text-embedding-3-small",
    ),
})
```

### No Audio Transcription

Claude does not have audio transcription capabilities. Use OpenAI Whisper or other providers for audio.

## API Differences

Claude's API differs from OpenAI in several ways:

| Feature | OpenAI | Claude |
|---------|--------|--------|
| Auth Header | `Authorization: Bearer <key>` | `x-api-key: <key>` |
| System Prompt | Message with role "system" | Top-level `system` parameter |
| Response Format | `choices[0].message.content` | `content[0].text` |
| Image Format | `image_url.url` | `source.type: "base64"` |

MemU handles these differences automatically through the backend abstraction.

## Error Handling

```python
from memu.llm.claude_sdk import ClaudeSDKClient

client = ClaudeSDKClient(api_key="your-key")

try:
    summary, _ = await client.summarize("text")
except Exception as e:
    if "rate_limit" in str(e).lower():
        # Handle rate limiting
        pass
    elif "invalid_api_key" in str(e).lower():
        # Handle auth error
        pass
    else:
        raise
```

## Best Practices

1. **Use appropriate models**: Claude Sonnet for most tasks, Opus for complex reasoning
2. **Set max_tokens**: Always specify to control costs and response length
3. **Use system prompts**: Claude responds well to clear instructions
4. **Handle embeddings separately**: Configure a dedicated embedding provider
5. **Monitor usage**: Track token usage via the response object

## Troubleshooting

### "anthropic package not installed"

```bash
pip install anthropic
```

### "Invalid API key"

- Verify your API key at [console.anthropic.com](https://console.anthropic.com/)
- Check the key is set correctly (no extra spaces)

### "Model not found"

- Verify the model name is correct
- Check your API key has access to the requested model

### Rate Limiting

Claude has rate limits based on your plan. Implement exponential backoff:

```python
import asyncio

async def summarize_with_retry(client, text, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await client.summarize(text)
        except Exception as e:
            if "rate_limit" in str(e).lower() and attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                raise
```
