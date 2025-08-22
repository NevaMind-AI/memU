# Docker Compose Configurations

This directory contains pre-configured Docker Compose files for different deployment scenarios of MemU.

## Available Configurations

| File | Purpose | Image Size | Startup Time | Best For |
|------|---------|------------|--------------|----------|
| `docker-compose.yml` | Standard server | ~500MB | ~15s | Production deployment |
| `docker-compose.minimal.yml` | Minimal setup | ~200MB | ~10s | Development & testing |
| `docker-compose.server-cpu.yml` | CPU-only server | ~500MB | ~15s | Resource-constrained environments |
| `docker-compose.local-cpu.yml` | Local models (CPU) | ~2GB | ~30s | Offline processing |
| `docker-compose.gpu.yml` | GPU-accelerated | ~3GB+ | ~45s | High-performance AI workloads |

## Quick Start

### Basic Usage
```bash
# From project root directory

# Minimal setup (recommended for testing)
docker-compose -f compose/docker-compose.minimal.yml up -d

# Standard deployment
docker-compose -f compose/docker-compose.yml up -d

# GPU-enabled (requires NVIDIA Docker)
docker-compose -f compose/docker-compose.gpu.yml up -d
```

### Prerequisites
1. Create environment file:
   ```bash
   cp env.example .env
   ```
2. Edit `.env` file with your API keys and configuration
3. Ensure Docker and Docker Compose are installed

## Configuration Details

### Standard (`docker-compose.yml`)
- **Dependencies**: Server packages without local models
- **Memory Usage**: ~1GB RAM
- **Features**: Full API, embeddings via external services
- **Use Case**: Production with cloud AI services

### Minimal (`docker-compose.minimal.yml`)
- **Dependencies**: Core packages only
- **Memory Usage**: ~512MB RAM  
- **Features**: REST API only, no embeddings
- **Use Case**: Development, testing, API gateway

### Server CPU (`docker-compose.server-cpu.yml`)
- **Dependencies**: Server packages, CPU-optimized
- **Memory Usage**: ~1GB RAM
- **Features**: Full API with embeddings
- **Use Case**: CPU-only production environments

### Local CPU (`docker-compose.local-cpu.yml`)
- **Dependencies**: Transformers, PyTorch CPU
- **Memory Usage**: ~2-4GB RAM
- **Features**: Local model processing
- **Use Case**: Offline deployments, privacy-focused setups

### GPU (`docker-compose.gpu.yml`)
- **Dependencies**: Full AI stack with GPU support
- **Memory Usage**: ~4GB+ RAM, 4GB+ VRAM
- **Features**: GPU-accelerated models
- **Use Case**: High-performance AI workloads
- **Requirements**: NVIDIA Container Toolkit, CUDA drivers

## Management Commands

```bash
# View logs
docker-compose -f compose/docker-compose.minimal.yml logs -f

# Stop services
docker-compose -f compose/docker-compose.minimal.yml down

# Rebuild
docker-compose -f compose/docker-compose.minimal.yml build --no-cache

# Switch configurations
docker-compose down                                        # Stop current
docker-compose -f compose/docker-compose.gpu.yml up -d   # Start new
```

## Environment Variables

All configurations use the same `.env` file. Key variables:

```bash
# LLM Provider (required)
MEMU_LLM_PROVIDER=openai
OPENAI_API_KEY=your-key-here

# Server settings
MEMU_HOST=0.0.0.0
MEMU_PORT=8000
MEMU_DEBUG=false

# Features
MEMU_ENABLE_EMBEDDINGS=true
MEMU_MEMORY_DIR=/app/memory
```

## Troubleshooting

### Common Issues
- **Port conflicts**: Change port mapping in compose file
- **Memory issues**: Use minimal configuration
- **GPU not detected**: Check NVIDIA Docker installation
- **Model download failures**: Pre-download models or use minimal setup

For detailed troubleshooting, see [README.self_host.md](../README.self_host.md#troubleshooting).

## More Information

- **Docker Build Options**: [DOCKER_BUILD_OPTIONS.md](../DOCKER_BUILD_OPTIONS.md)
- **Compose Configurations**: [COMPOSE_CONFIGURATIONS.md](../COMPOSE_CONFIGURATIONS.md)
- **Self-hosting Guide**: [README.self_host.md](../README.self_host.md)
