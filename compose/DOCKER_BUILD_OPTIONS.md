# Docker Build Options

This document explains how to build the MemU Docker image with different configurations to control GPU and non-GPU dependencies.

## Build Arguments

The Dockerfile supports the following build arguments:

- `INSTALL_MODE`: Controls which dependency groups to install
  - `server` (default): Standard server dependencies
  - `minimal`: Minimal server setup without embeddings
  - `llm`: LLM provider dependencies
  - `dev`: Development dependencies
  - `all`: All dependencies

- `INCLUDE_GPU`: Controls GPU support
  - `false` (default): CPU-only dependencies
  - `true`: Include GPU support

- `INCLUDE_LOCAL_MODELS`: Controls local model support
  - `false` (default): No local model dependencies
  - `true`: Include local model dependencies (transformers, torch)

## Build Examples

### 1. Minimal CPU-Only Server (Recommended for production without GPU)
```bash
docker build -t memu:minimal \
  --build-arg INSTALL_MODE=minimal \
  --build-arg INCLUDE_GPU=false \
  --build-arg INCLUDE_LOCAL_MODELS=false \
  .
```

### 2. Standard Server without GPU (Default)
```bash
docker build -t memu:server-cpu \
  --build-arg INSTALL_MODE=server \
  --build-arg INCLUDE_GPU=false \
  .
```

### 3. Server with CPU-only Local Models
```bash
docker build -t memu:server-local-cpu \
  --build-arg INSTALL_MODE=server \
  --build-arg INCLUDE_GPU=false \
  --build-arg INCLUDE_LOCAL_MODELS=true \
  .
```

### 4. Server with GPU Support
```bash
docker build -t memu:server-gpu \
  --build-arg INSTALL_MODE=server \
  --build-arg INCLUDE_GPU=true \
  --build-arg INCLUDE_LOCAL_MODELS=true \
  .
```

### 5. Development Environment
```bash
docker build -t memu:dev \
  --build-arg INSTALL_MODE=dev \
  --build-arg INCLUDE_GPU=false \
  .
```

### 6. Full Installation with All Dependencies
```bash
docker build -t memu:full \
  --build-arg INSTALL_MODE=all \
  --build-arg INCLUDE_GPU=true \
  --build-arg INCLUDE_LOCAL_MODELS=true \
  .
```

## Dependency Groups Explanation

### Minimal (`minimal`)
- Basic web server (uvicorn, fastapi)
- No embeddings or ML dependencies
- Smallest image size
- Best for API-only deployments

### Server CPU (`server-cpu`)
- Standard server functionality
- CPU-only embeddings (if any)
- No GPU dependencies
- Good for cloud deployments without GPU

### Server (`server`)
- Standard server functionality
- Includes sentence-transformers (may download models)
- Default configuration

### LLM (`llm`)
- Provider API clients (OpenAI, Anthropic, etc.)
- No local model processing
- Good for API-based AI services

### Local (`local`)
- Local model processing capabilities
- Includes transformers and torch
- Can be CPU-only or GPU-enabled based on INCLUDE_GPU

### All (`all`)
- All available dependencies
- Largest image size
- Full functionality

## Image Size Comparison

| Configuration | Estimated Size | Use Case |
|---------------|----------------|----------|
| Minimal | ~200MB | API server only |
| Server-CPU | ~500MB | Standard server, no GPU |
| Server-Local-CPU | ~2GB | Local models, CPU only |
| Server-GPU | ~3GB+ | GPU-enabled server |
| Full | ~4GB+ | Development/testing |

## Usage in Docker Compose

You can specify build arguments in your compose files (located in `compose/` directory):

```yaml
services:
  memu:
    build:
      context: ..
      args:
        INSTALL_MODE: server
        INCLUDE_GPU: false
        INCLUDE_LOCAL_MODELS: false
    ports:
      - "8000:8000"
```

Use the pre-configured compose files:

```bash
# Minimal setup
docker-compose -f compose/docker-compose.minimal.yml up -d

# Standard server (CPU-only)
docker-compose -f compose/docker-compose.yml up -d

# GPU-enabled setup
docker-compose -f compose/docker-compose.gpu.yml up -d
```

## Notes

- CPU-only torch installations use the PyTorch CPU wheel for faster downloads and smaller size
- GPU builds require appropriate CUDA base image (consider using nvidia/python:3.11-runtime)
- Local models will be downloaded at runtime, which may increase startup time
- For production, consider using multi-stage builds to reduce final image size
