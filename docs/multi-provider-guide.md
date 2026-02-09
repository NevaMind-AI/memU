# Multi-Provider Setup Guide

This fork adds **Anthropic (Claude)** and **Gemini** as LLM/embedding providers.

## Provider Configuration Examples

### Anthropic (Claude) + Gemini Embeddings

```yaml
llm:
  provider: anthropic
  base_url: https://api.anthropic.com
  api_key: sk-ant-api03-...
  chat_model: claude-sonnet-4-5-20250514
  client_backend: httpx

  # Use Gemini for embeddings (Anthropic doesn't offer embedding models)
  embed_provider: gemini
  embed_base_url: https://generativelanguage.googleapis.com
  embed_api_key: AIza...
  embed_model: text-embedding-004
```

### Gemini (Google AI Studio)

```yaml
llm:
  provider: gemini
  base_url: https://generativelanguage.googleapis.com
  api_key: AIza...
  chat_model: gemini-2.0-flash
  client_backend: httpx
  embed_model: text-embedding-004
```

### OpenAI (default, unchanged)

```yaml
llm:
  provider: openai
  base_url: https://api.openai.com/v1
  api_key: sk-...
  chat_model: gpt-4o-mini
  client_backend: sdk
  embed_model: text-embedding-3-small
```

## What Changed

### New Providers
- **`anthropic`** LLM backend — supports both `x-api-key` and `Bearer` auth (OAuth tokens starting with `sk-ant-oat`)
- **`gemini`** LLM backend — Google AI Studio API format (`/models/{model}:generateContent`)
- **`gemini`** embedding backend — Google AI Studio embeddings (`/models/{model}:embedContent`)

### Separate Embedding Provider
You can use a different provider for embeddings vs LLM:
- `embed_provider` — override the embedding provider (e.g., use `gemini` embeddings with `anthropic` LLM)
- `embed_api_key` — separate API key for embedding provider
- `embed_base_url` — separate base URL for embedding provider

### SQLite Fixes
- Table names: `sqlite_*` → `memu_*`
- Fixed Pydantic serialization errors with embedding fields
- `resource_id` is now optional (allows memory items without resources)
- `model_config = ConfigDict(extra="allow")` for dynamic attributes

## Installation

```bash
pip install git+https://github.com/murasame-desu-ai/memU.git@feat/multi-provider-sqlite
```
