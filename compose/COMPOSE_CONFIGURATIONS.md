# Docker Compose Configurations

This directory contains multiple Docker Compose configurations optimized for different use cases.

## Quick Reference

| File | Image Size | Startup Time | Use Case |
|------|------------|--------------|----------|
| `compose/docker-compose.minimal.yml` | ~200MB | ~10s | API-only, development |
| `compose/docker-compose.yml` | ~500MB | ~15s | Standard deployment |
| `compose/docker-compose.server-cpu.yml` | ~500MB | ~15s | CPU-only server |
| `compose/docker-compose.local-cpu.yml` | ~2GB | ~30s | Offline processing |
| `compose/docker-compose.gpu.yml` | ~3GB+ | ~45s | High-performance AI |

## Configuration Details

### compose/docker-compose.minimal.yml
- **Purpose**: Lightweight API server
- **Dependencies**: Minimal Python packages
- **Memory**: ~512MB RAM
- **Features**: REST API only, no embeddings
- **Best for**: Development, testing, API gateway

```bash
docker-compose -f compose/docker-compose.minimal.yml up -d
```

### compose/docker-compose.yml (Default)
- **Purpose**: Standard server deployment
- **Dependencies**: Server packages without local models
- **Memory**: ~1GB RAM
- **Features**: Full API, embeddings via external services
- **Best for**: Production with cloud AI services

```bash
docker-compose up -d
```

### compose/docker-compose.server-cpu.yml
- **Purpose**: CPU-only server without heavy dependencies
- **Dependencies**: Server packages, CPU-optimized
- **Memory**: ~1GB RAM
- **Features**: Full API, embeddings
- **Best for**: Resource-constrained environments

```bash
docker-compose -f compose/docker-compose.server-cpu.yml up -d
```

### compose/docker-compose.local-cpu.yml
- **Purpose**: Local model processing (CPU-only)
- **Dependencies**: Transformers, PyTorch CPU, sentence-transformers
- **Memory**: ~2-4GB RAM
- **Features**: Local embeddings, offline processing
- **Best for**: Offline deployments, privacy-focused setups

```bash
docker-compose -f compose/docker-compose.local-cpu.yml up -d
```

### compose/docker-compose.gpu.yml
- **Purpose**: GPU-accelerated AI processing
- **Dependencies**: Full AI stack with GPU support
- **Memory**: ~4GB+ RAM, 4GB+ VRAM
- **Features**: GPU-accelerated models, high throughput
- **Best for**: High-performance AI workloads
- **Requirements**: NVIDIA Docker, CUDA drivers

```bash
docker-compose -f compose/docker-compose.gpu.yml up -d
```

## Switching Between Configurations

```bash
# Stop current configuration
docker-compose down

# Start different configuration
docker-compose -f compose/docker-compose.minimal.yml up -d
```

## Environment Variables

All configurations use the same `.env` file. Key variables:

```bash
# Required for all configurations
MEMU_LLM_PROVIDER=openai
OPENAI_API_KEY=your-key-here

# Optional optimizations
MEMU_ENABLE_EMBEDDINGS=true    # Set to false for minimal setups
MEMU_DEBUG=false               # Set to true for development
MEMU_MEMORY_DIR=/app/memory    # Data persistence location
```

## Volume Management

Each configuration uses named volumes:

- `memu-memory`: Persistent memory storage
- `memu-logs`: Application logs
- `memu-models`: Model cache (local-cpu and gpu only)

```bash
# View volumes
docker volume ls | grep memu

# Backup memory data
docker run --rm -v memu-memory:/data -v $(pwd):/backup alpine tar czf /backup/memu-memory-backup.tar.gz -C /data .

# Restore memory data
docker run --rm -v memu-memory:/data -v $(pwd):/backup alpine tar xzf /backup/memu-memory-backup.tar.gz -C /data
```

## Performance Comparison

### Startup Times (approximate)
- Minimal: 10-15 seconds
- Standard: 15-20 seconds  
- Server-CPU: 15-20 seconds
- Local-CPU: 30-45 seconds (first run), 15-20 seconds (subsequent)
- GPU: 45-60 seconds (first run), 20-30 seconds (subsequent)

### Memory Usage
- Minimal: 256MB - 512MB
- Standard: 512MB - 1GB
- Server-CPU: 512MB - 1GB
- Local-CPU: 1GB - 4GB (depends on models)
- GPU: 2GB - 8GB+ (depends on models and VRAM)

## Troubleshooting

### Configuration not starting
```bash
# Check logs
docker-compose -f <config-file> logs -f memu-server

# Verify configuration
docker-compose -f <config-file> config
```

### Out of memory
```bash
# Switch to lighter configuration
docker-compose down
docker-compose -f compose/docker-compose.minimal.yml up -d
```

### Model download issues (local-cpu/gpu)
```bash
# Pre-download models
docker-compose -f <config-file> run --rm memu-server python -c "
import sentence_transformers
model = sentence_transformers.SentenceTransformer('all-MiniLM-L6-v2')
"
```
