# MemU Assistant - Sealos DevBox Example

A personal AI assistant with long-term memory, designed for deployment on [Sealos DevBox](https://sealos.io/products/devbox).

## Features

- **Persistent Memory**: Remembers user preferences and past conversations
- **REST API**: Simple endpoints for chat, memorize, and recall
- **OpenAI Compatible**: Works with OpenAI, Nebius, Groq, and other providers
- **1-Click Deploy**: Ready for Sealos DevBox deployment

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API key

# Run the server
python main.py
```

### Deploy on Sealos DevBox

1. Create a Python DevBox on [Sealos](https://cloud.sealos.io)
2. Clone this project
3. Set environment variables
4. Click **Deploy**

See the full guide: [docs/sealos-devbox-guide.md](../../docs/sealos-devbox-guide.md)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info |
| `/health` | GET | Health check |
| `/chat` | POST | Chat with memory |
| `/memorize` | POST | Store information |
| `/recall` | GET | Query memories |

## Example Usage

```bash
# Store a memory
curl -X POST http://localhost:8000/memorize \
  -H "Content-Type: application/json" \
  -d '{"content": "I prefer Python and dark mode"}'

# Chat with memory
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are my preferences?"}'

# Recall memories
curl "http://localhost:8000/recall?query=preferences"
```

## License

MIT - Part of the MemU project
