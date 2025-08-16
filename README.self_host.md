# 🐳 MemU Self-Host (Docker Compose)

Get the MemU server running locally with Docker Compose. This guide covers configuration, startup, verification, testing, persistence, and troubleshooting.

## Prerequisites

- Docker and Docker Compose
- At least one LLM provider API key

## 🚀 Quick Start (3 steps)

### 1) Configure environment

```bash
# Copy the root template and edit values
cp env.example .env

# OpenAI (default provider)
echo "OPENAI_API_KEY=your-openai-api-key" >> .env

# Optional: choose provider in .env (openai | deepseek | azure)
# MEMU_LLM_PROVIDER=openai
```

Key variables from `.env` used by the server:

- MEMU_HOST (default 0.0.0.0)
- MEMU_PORT (default 8000)
- MEMU_DEBUG (default false)
- MEMU_MEMORY_DIR (default memu/server/memory; default in container is /app/memory/server)
- MEMU_LLM_PROVIDER (openai | deepseek | azure)
- MEMU_ENABLE_EMBEDDINGS (default true)

LLM-specific settings are documented below.

### 2) Start the server

```bash
docker-compose up -d
```

This uses `docker-compose.yml` to build and launch the `memu-server` container, mapping host port 8000 → container port 8000 and persisting data to named volumes.

### 3) Verify

```bash
# Health
curl http://localhost:8000/health

# API docs
open http://localhost:8000/docs

# Logs (optional)
docker-compose logs -f memu-server
```

## 🌐 Endpoints

- API Base: <http://localhost:8000>
- API Docs: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

## 🧪 Test the server

```bash
python example/server/test_server.py
```

This script runs an end-to-end flow: health check, memorize, task status, and retrieval. If embeddings are enabled, ensure a valid embedding model and API key are configured.

## ⚙️ Configuration reference

Edit `.env` to configure the server. Common options:

- MEMU_HOST: bind address (default 0.0.0.0)
- MEMU_PORT: port (default 8000)
- MEMU_DEBUG: auto-reload and verbose logs (true/false)
- MEMU_MEMORY_DIR: on-disk memory path inside the container (default /app/memory via entrypoint)
- MEMU_ENABLE_EMBEDDINGS: enable vector embeddings (true/false)
- MEMU_CORS_ORIGINS: CORS origins (e.g. \*, <http://localhost:3000>)
- MEMU_LLM_PROVIDER: openai | deepseek | azure | openrouter

### OpenAI

```bash
MEMU_LLM_PROVIDER=openai 
OPENAI_API_KEY=your-openai-api-key
MEMU_OPENAI_MODEL=gpt-4.1-mini
MEMU_EMBEDDING_MODEL=text-embedding-3-small
```

### DeepSeek

```bash
MEMU_LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_VERSION=2024-05-01-preview
MEMU_DEEPSEEK_MODEL=deepseek-chat
```

### Azure OpenAI

```bash
MEMU_LLM_PROVIDER=azure
AZURE_API_KEY=your-azure-api-key
AZURE_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_API_VERSION=2025-01-01-preview
MEMU_AZURE_DEPLOYMENT_NAME=gpt-4.1-mini
MEMU_EMBEDDING_MODEL=text-embedding-3-small
```

### OpenRouter

```bash
MEMU_LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your-openrouter-api-key
MEMU_OPENROUTER_MODEL=openrouter/auto
```

Note: The container entrypoint validates required keys for the selected provider before starting.

## 💾 Data persistence and logs

The Compose file defines named volumes:

- memu-memory → mounted at `/app/memory` (or `${MEMU_MEMORY_DIR}`)
- memu-logs → mounted at `/app/logs`

To inspect data on the host, use Docker Desktop or `docker volume inspect` and mount the volume into a temporary container.

## 🔧 Management

```bash
# View logs
docker-compose logs -f memu-server

# Restart
docker-compose restart memu-server

# Stop
docker-compose down

# Rebuild and start clean
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 🐛 Troubleshooting

### Port 8000 already in use

Option A: override at runtime

```bash
MEMU_PORT=8001 docker-compose up -d
```

Option B: edit `docker-compose.yml` ports mapping, e.g. `"8001:8000"`.

### API key or provider errors

```bash
cat .env
# Ensure the correct provider is set and required keys exist
# e.g. OPENAI_API_KEY, or DEEPSEEK_API_KEY, or AZURE_API_KEY + AZURE_ENDPOINT + MEMU_AZURE_DEPLOYMENT_NAME
```

### Long memory processing times

- Verify rate limits and quotas on your LLM account
- Reduce payload size while testing
- Check logs: `docker-compose logs -f memu-server`

### Shell access

```bash
docker-compose exec memu-server bash
```

## 📚 More information

For a deeper dive into features, endpoints, and development usage, see `memu/server/README.md`.
