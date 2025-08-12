# MemU Server Docker Setup

This directory contains Docker configurations for running the MemU server in a containerized environment.

## Quick Start

### 1. Setup Environment Variables

Copy the environment template and configure your API keys:

```bash
cp env.example .env
# Edit .env file and add your API keys
```

### 2. Build and Run with Docker Compose

```bash
# Start the server
docker-compose up -d

# View logs
docker-compose logs -f memu-server

# Stop the server
docker-compose down
```

### 3. Access the Server

- **API Base URL**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Manual Docker Commands

### Build Image

```bash
docker build -t memu-server .
```

### Run Container

```bash
# Basic run
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your-key-here \
  memu-server

# Run with persistent storage
docker run -p 8000:8000 \
  -v memu-memory:/app/memory \
  -e OPENAI_API_KEY=your-key-here \
  memu-server

# Run with custom configuration
docker run -p 8000:8000 \
  -v $(pwd)/.env:/app/.env \
  -v memu-memory:/app/memory \
  memu-server
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MEMU_HOST` | Server host address | `0.0.0.0` |
| `MEMU_PORT` | Server port | `8000` |
| `MEMU_DEBUG` | Enable debug mode | `false` |
| `MEMU_LLM_PROVIDER` | LLM provider (openai, anthropic, deepseek, azure) | `openai` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `DEEPSEEK_API_KEY` | DeepSeek API key | - |

See `env.example` for a complete list of configuration options.

### Volumes

- `/app/memory` - Persistent memory storage
- `/app/logs` - Application logs (optional)

## Development

### Build Development Image

```bash
docker build -t memu-server:dev \
  --build-arg ENVIRONMENT=development .
```

### Run with Hot Reload

```bash
docker run -p 8000:8000 \
  -v $(pwd):/app \
  -e MEMU_DEBUG=true \
  memu-server:dev
```

## Production Deployment

### Docker Compose Production

```bash
# Use production configuration
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Health Monitoring

The container includes health checks that monitor:
- Server responsiveness on `/health` endpoint
- Container resource usage
- API availability

### Scaling

```bash
# Scale to multiple instances
docker-compose up -d --scale memu-server=3
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Check what's using port 8000
   lsof -i :8000
   ```

2. **Permission denied for memory directory**
   ```bash
   # Fix directory permissions
   sudo chown -R 1000:1000 ./memory
   ```

3. **API key not found**
   - Ensure your `.env` file exists and contains valid API keys
   - Check environment variable names match the expected format

### Logs

```bash
# View container logs
docker-compose logs memu-server

# Follow logs in real-time
docker-compose logs -f memu-server

# View specific service logs
docker logs memu-server
```

### Container Shell Access

```bash
# Access running container
docker-compose exec memu-server bash

# Run one-off command
docker-compose run --rm memu-server bash
```

## Security Considerations

- Never commit `.env` files with real API keys to version control
- Use Docker secrets for production deployments
- Regularly update the base Python image for security patches
- Consider running containers with read-only root filesystem
- Implement proper network segmentation in production

## Performance Tuning

- Adjust memory limits based on your usage patterns
- Use multi-stage builds to reduce image size
- Consider using distroless base images for production
- Implement proper caching strategies for dependencies
