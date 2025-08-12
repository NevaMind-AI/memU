# 🐳 MemU Server Docker Quick Start

Get MemU server running in Docker with just a few commands!

## Prerequisites

- Docker and Docker Compose installed
- Your LLM provider API key

## 🚀 Quick Start (3 steps)

### 1. Configure Environment

```bash
# Copy environment template
cp env.example .env

# Edit .env and add your API key
# For OpenAI (default):
echo "OPENAI_API_KEY=your-api-key-here" >> .env

# For other providers, edit .env file and set:
# MEMU_LLM_PROVIDER=anthropic (or deepseek, azure)
# ANTHROPIC_API_KEY=your-key-here
```

### 2. Start the Server

```bash
docker-compose up -d
```

### 3. Verify it's Working

```bash
# Check status
curl http://localhost:8000/health

# View logs
docker-compose logs -f memu-server
```

## 🌐 Access Points

- **API Base**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs  
- **Health Check**: http://localhost:8000/health

## 🛠️ Management Commands

```bash
# View logs
docker-compose logs memu-server

# Stop server
docker-compose down

# Restart server
docker-compose restart memu-server

# Update and rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 🐛 Troubleshooting

**Port 8000 already in use?**
```bash
# Use different port
docker-compose up -d --env MEMU_PORT=8001
```

**API key errors?**
```bash
# Check your .env file
cat .env
# Make sure OPENAI_API_KEY (or your provider's key) is set
```

**Need shell access?**
```bash
docker-compose exec memu-server bash
```

## 📚 More Info

For detailed configuration and production deployment, see `README.docker.md`.
