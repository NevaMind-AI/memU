# 🐳 MemU Self-Host (Docker Compose)

Get the MemU server running locally with Docker Compose. This guide covers configuration, startup, verification, testing, persistence, and troubleshooting.

## Prerequisites

- Docker and Docker Compose
- At least one LLM provider API key

## 🏗️ Docker Build Options

MemU supports different Docker configurations to optimize for various deployment scenarios. Choose the build option that best fits your needs:

### Available Build Modes

| Mode | Image Size | Use Case | GPU Support | Local Models |
|------|------------|----------|-------------|--------------|
| `minimal` | ~200MB | API-only server | ❌ | ❌ |
| `server` | ~500MB | Standard deployment | Optional | Optional |
| `server-cpu` | ~500MB | CPU-only server | ❌ | ❌ |
| `local-cpu` | ~2GB | Local models (CPU) | ❌ | ✅ |
| `gpu` | ~3GB+ | GPU-accelerated | ✅ | ✅ |

### Quick Build Commands

#### Minimal Setup (Recommended for most users)
```bash
# Lightweight API server without heavy dependencies
docker build -t memu:minimal \
  --build-arg INSTALL_MODE=minimal \
  --build-arg INCLUDE_GPU=false \
  .
```

#### Standard CPU-Only (Default)
```bash
# Standard server functionality without GPU dependencies
docker build -t memu:server-cpu \
  --build-arg INSTALL_MODE=server \
  --build-arg INCLUDE_GPU=false \
  .
```

#### GPU-Enabled Setup
```bash
# Full server with GPU support for local models
docker build -t memu:gpu \
  --build-arg INSTALL_MODE=server \
  --build-arg INCLUDE_GPU=true \
  --build-arg INCLUDE_LOCAL_MODELS=true \
  .
```

### Docker Compose with Build Options

Create different compose files for different setups:

**compose/docker-compose.minimal.yml** (Lightest setup):
```yaml
services:
  memu-server:
    build:
      context: .
      args:
        INSTALL_MODE: minimal
        INCLUDE_GPU: false
        INCLUDE_LOCAL_MODELS: false
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - memu-memory:/app/memory
      - memu-logs:/app/logs
    restart: unless-stopped

volumes:
  memu-memory:
  memu-logs:
```

**compose/docker-compose.gpu.yml** (GPU support):
```yaml
services:
  memu-server:
    build:
      context: .
      args:
        INSTALL_MODE: server
        INCLUDE_GPU: true
        INCLUDE_LOCAL_MODELS: true
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - memu-memory:/app/memory
      - memu-logs:/app/logs
      - memu-models:/app/models
    environment:
      - CUDA_VISIBLE_DEVICES=0
    restart: unless-stopped

volumes:
  memu-memory:
  memu-logs:
  memu-models:
```

### Available Docker Compose Files

| File | Configuration | Best For |
|------|---------------|----------|
| `compose/docker-compose.yml` | Standard server (CPU-only) | Default deployment |
| `compose/docker-compose.minimal.yml` | Minimal setup | Lightweight API server |
| `compose/docker-compose.server-cpu.yml` | Server without embeddings | CPU-only server |
| `compose/docker-compose.local-cpu.yml` | Local models (CPU-only) | Offline processing |
| `compose/docker-compose.gpu.yml` | GPU-enabled with local models | High-performance setup |

### Usage with Different Configurations

```bash
# Use minimal setup (fastest startup, smallest image)
docker-compose -f compose/docker-compose.minimal.yml up -d

# Use standard CPU-only server (default - same as docker-compose up -d)
docker-compose -f compose/docker-compose.server-cpu.yml up -d

# Use local models with CPU-only processing
docker-compose -f compose/docker-compose.local-cpu.yml up -d

# Use GPU setup (requires NVIDIA Docker support)
docker-compose -f compose/docker-compose.gpu.yml up -d

# Use default setup (standard server, CPU-only)
docker-compose up -d
```

> 💡 **Recommendation**: Start with the `minimal` build for initial testing and API-only usage. Upgrade to `server` or `gpu` configurations only if you need local model processing capabilities.

> ⚠️ **GPU Requirements**: GPU builds require NVIDIA Container Toolkit and compatible NVIDIA drivers. See [DOCKER_BUILD_OPTIONS.md](DOCKER_BUILD_OPTIONS.md) for detailed setup instructions.

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

Choose your preferred configuration:

**Option A: Minimal setup (fastest, recommended for most users)**
```bash
# Use the provided minimal configuration
docker-compose -f compose/docker-compose.minimal.yml up -d
```

**Option B: Default setup**
```bash
docker-compose up -d
```

**Option C: Custom build**
```bash
# Build with specific options first
docker build -t memu:custom \
  --build-arg INSTALL_MODE=server \
  --build-arg INCLUDE_GPU=false \
  .

# Then run with the custom image
docker run -d \
  --name memu-server \
  -p 8000:8000 \
  --env-file .env \
  -v memu-memory:/app/memory \
  -v memu-logs:/app/logs \
  memu:custom
```

This builds and launches the `memu-server` container, mapping host port 8000 → container port 8000 and persisting data to named volumes.

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

### Basic Management

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

### Managing Different Configurations

```bash
# For minimal setup
docker-compose -f compose/docker-compose.minimal.yml logs -f memu-server
docker-compose -f compose/docker-compose.minimal.yml down
docker-compose -f compose/docker-compose.minimal.yml build --no-cache

# For server-cpu setup
docker-compose -f compose/docker-compose.server-cpu.yml logs -f memu-server
docker-compose -f compose/docker-compose.server-cpu.yml down

# For local-cpu setup
docker-compose -f compose/docker-compose.local-cpu.yml logs -f memu-server
docker-compose -f compose/docker-compose.local-cpu.yml down

# For GPU setup
docker-compose -f compose/docker-compose.gpu.yml logs -f memu-server
docker-compose -f compose/docker-compose.gpu.yml down

# Switch between configurations
docker-compose down                                      # Stop current
docker-compose -f compose/docker-compose.minimal.yml up -d     # Start minimal
docker-compose -f compose/docker-compose.local-cpu.yml up -d   # Start local-cpu
docker-compose -f compose/docker-compose.gpu.yml up -d         # Start GPU
```

### Image Management

```bash
# List MemU images
docker images | grep memu

# Remove old images
docker image prune -f

# Rebuild specific configuration
docker build -t memu:minimal \
  --build-arg INSTALL_MODE=minimal \
  --build-arg INCLUDE_GPU=false \
  --no-cache \
  .
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

### Build-related issues

#### "No space left on device" during build
```bash
# Clean up Docker system
docker system prune -a --volumes

# Check available space
df -h

# Use minimal build if space is limited
docker build -t memu:minimal \
  --build-arg INSTALL_MODE=minimal \
  --build-arg INCLUDE_GPU=false \
  .
```

#### GPU not detected (for GPU builds)
```bash
# Check NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi

# Verify GPU configuration
docker-compose -f compose/docker-compose.gpu.yml config

# Try running without GPU temporarily
docker-compose -f compose/docker-compose.minimal.yml up -d
```

#### Memory issues with large models
```bash
# Use CPU-only builds with smaller models
docker build -t memu:server-cpu \
  --build-arg INSTALL_MODE=server \
  --build-arg INCLUDE_GPU=false \
  .

# Or increase Docker Desktop memory limit (macOS/Windows)
# Settings > Resources > Memory
```

#### Slow model downloads
```bash
# Use minimal build for API-only usage (no model downloads)
docker-compose -f compose/docker-compose.minimal.yml up -d

# Or pre-download models and mount them
mkdir -p ./models
docker run -v ./models:/app/models memu:gpu python -c "import sentence_transformers; sentence_transformers.SentenceTransformer('all-MiniLM-L6-v2')"
```

### Shell access

```bash
docker-compose exec memu-server bash

# For specific configurations
docker-compose -f compose/docker-compose.minimal.yml exec memu-server bash
docker-compose -f compose/docker-compose.server-cpu.yml exec memu-server bash
docker-compose -f compose/docker-compose.local-cpu.yml exec memu-server bash
docker-compose -f compose/docker-compose.gpu.yml exec memu-server bash
```

## 📚 More information

- For detailed Docker build options and configurations: [DOCKER_BUILD_OPTIONS.md](DOCKER_BUILD_OPTIONS.md)
- For features, endpoints, and development usage: `memu/server/README.md`
- For GPU setup requirements: [DOCKER_BUILD_OPTIONS.md#docker-installation-requirements](DOCKER_BUILD_OPTIONS.md#docker-installation-requirements)
