# MemU Self-Hosted Server

A FastAPI-based self-hosted server for the MemU memory management system.

## Features

- **Memory Storage**: Store and process conversation memories
- **Semantic Search**: Find related memories using vector embeddings
- **Multiple LLM Support**: OpenAI, Anthropic, and DeepSeek
- **REST API**: Full REST API compatible with MemU SDK
- **Background Tasks**: Asynchronous memory processing
- **Easy Deployment**: Single binary deployment with Docker support

## Quick Start

### 1. Install Dependencies

```bash
# Install MemU with server dependencies
pip install -e ".[server]"

# Or install server requirements directly
pip install -r memu/server/requirements.txt
```

### 2. Configuration

Create a `.env` file:

```bash
# Copy template
cp memu/server/.env.example .env

# Edit configuration
nano .env
```

Required configuration:
- Set your LLM API key (OpenAI, Anthropic, or DeepSeek)
- Choose your LLM provider
- Configure memory directory path

### 3. Start Server

```bash
# Using CLI tool
python -m memu.server.cli start

# Or directly with uvicorn
uvicorn memu.server.main:app --host 0.0.0.0 --port 8000
```

### 4. Test API

Open http://localhost:8000/docs for interactive API documentation.

## API Endpoints

### Memory Storage

- `POST /api/v1/memory/memorize` - Start memorization task
- `GET /api/v1/memory/memorize/status/{task_id}` - Get task status

### Memory Retrieval

- `POST /api/v1/memory/retrieve/default-categories` - Get default categories
- `POST /api/v1/memory/retrieve/related-memory-items` - Search memory items
- `POST /api/v1/memory/retrieve/related-clustered-categories` - Search categories

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MEMU_HOST` | Server host | `0.0.0.0` |
| `MEMU_PORT` | Server port | `8000` |
| `MEMU_DEBUG` | Debug mode | `false` |
| `MEMU_MEMORY_DIR` | Memory storage directory | `./memu/server/memory` |
| `MEMU_LLM_PROVIDER` | LLM provider (openai/anthropic/deepseek) | `openai` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `DEEPSEEK_API_KEY` | DeepSeek API key | - |

### LLM Providers

#### OpenAI
```bash
MEMU_LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
MEMU_OPENAI_MODEL=gpt-4
```


#### DeepSeek
```bash
MEMU_LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_key_here
MEMU_DEEPSEEK_MODEL=deepseek-chat
```

## Usage Examples

### Using MemU SDK Client

```python
from memu import MemuClient

# Initialize client
client = MemuClient(base_url="http://localhost:8000")

# Memorize conversation
response = client.memorize_conversation(
    conversation="User: Hello\nAssistant: Hi there!",
    user_id="user123",
    user_name="John Doe",
    agent_id="agent456",
    agent_name="Assistant"
)

print(f"Task ID: {response.task_id}")

# Check task status
status = client.get_task_status(response.task_id)
print(f"Status: {status.status}")

# Retrieve memories
memories = client.retrieve_related_memory_items(
    user_id="user123",
    agent_id="agent456",
    query="greetings"
)

print(f"Found {len(memories.related_memories)} related memories")
```

### Using HTTP Requests

```bash
# Memorize conversation
curl -X POST "http://localhost:8000/api/v1/memory/memorize" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_text": "User: Hello\nAssistant: Hi there!",
    "user_id": "user123",
    "user_name": "John Doe",
    "agent_id": "agent456",
    "agent_name": "Assistant"
  }'

# Check task status
curl "http://localhost:8000/api/v1/memory/memorize/status/{task_id}"

# Search memories
curl -X POST "http://localhost:8000/api/v1/memory/retrieve/related-memory-items" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "agent_id": "agent456",
    "query": "greetings",
    "top_k": 10
  }'
```

## Development

### Running in Development Mode

```bash
# Enable debug mode
export MEMU_DEBUG=true

# Start with auto-reload
python -m memu.server.cli start --debug
```

### Project Structure

```
memu/server/
├── __init__.py          # Package initialization
├── main.py              # FastAPI application
├── config.py            # Configuration management
├── middleware.py        # Custom middleware
├── models.py            # Pydantic models
├── cli.py               # Command line interface
├── requirements.txt     # Server dependencies
├── .env.example         # Configuration template
├── routers/             # API route handlers
│   ├── __init__.py
│   └── memory.py        # Memory endpoints
└── services/            # Business logic
    ├── __init__.py
    ├── memory_service.py # Memory operations
    └── task_service.py   # Task management
```

## Deployment

### Docker (Future)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -e ".[server]"

EXPOSE 8000
CMD ["python", "-m", "memu.server.cli", "start"]
```

### Production

For production deployment:

1. Set `MEMU_DEBUG=false`
2. Use a production ASGI server like Gunicorn
3. Configure proper logging
4. Set up reverse proxy (nginx)
5. Enable HTTPS
6. Configure monitoring

## Troubleshooting

### Common Issues

1. **Missing API Key**: Ensure your LLM provider API key is set
2. **Memory Directory**: Check that memory directory is writable
3. **Port Conflicts**: Change port if 8000 is already in use
4. **Embeddings**: Vector embeddings require additional dependencies

### Logs

Enable debug logging:

```bash
export MEMU_DEBUG=true
python -m memu.server.cli start --debug
```

## License

This project is licensed under the same license as the main MemU package.
