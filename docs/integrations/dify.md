# Dify Integration for MemU

This guide explains how to integrate MemU with [Dify](https://dify.ai) to allow your Dify Agents to store and retrieve information from MemU's long-term memory.

## Overview

The integration uses Dify's **API-based Tool** capability. You will host a small lightweight Python server (Adapter) that exposes MemU functionality, and then register it in Dify using an OpenAPI specification.

## Prerequisites

- MemU installed (`pip install memu-py`)
- Python 3.13+
- Dify instance (Cloud or Self-hosted)

## 1. Host the MemU Adapter

Since MemU is a library, you need to expose it via an API server. Below is a complete example using **FastAPI**.

### `server.py`

```python
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from contextlib import asynccontextmanager

from memu import MemUService
from memu.integrations.dify import DifyToolProvider

# Configuration
API_KEY = "your-secret-key"
HOST = "0.0.0.0"
PORT = 8000

# Global services
services = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize MemU Service
    # Ensure you have your environment variables set (e.g., OPENAI_API_KEY)
    memu_service = MemUService()
    dify_provider = DifyToolProvider(memu_service, api_key=API_KEY)

    services["dify"] = dify_provider
    yield
    # Cleanup if necessary

app = FastAPI(lifespan=lifespan)

class MemoryRequest(BaseModel):
    query: str
    user_id: str | None = None

def verify_token(token: str):
    if token != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

@app.post("/add-memory")
async def add_memory(request: MemoryRequest):
    """Endpoint for Dify to add memory."""
    provider = services["dify"]
    return await provider.add_memory(request.query, request.user_id)

@app.post("/search-memory")
async def search_memory(request: MemoryRequest):
    """Endpoint for Dify to search memory."""
    provider = services["dify"]
    return await provider.search_memory(request.query, request.user_id)

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
```

Run the server:
```bash
uv run python server.py
# or
pip install fastapi uvicorn
python server.py
```

## 2. Configure Dify

1. **Log in to Dify**.
2. Go to **Tools** > **API-based Tool** > **Create**.
3. **Import OpenAPI Schema**:
   - Copy the content of [`Docs > Integrations > dify-openapi.yaml`](dify-openapi.yaml).
   - Paste it into the Dify definition editor.
   - Update the `servers.url` in the YAML if your server is not on `localhost`. If you are using Dify Cloud, use a public URL (e.g., via ngrok).
4. **Authentication**:
   - Select **Bearer Auth**.
   - Enter the API Key you defined in `server.py` (e.g., `your-secret-key`).
5. **Save** the tool.

## 3. Use in Dify Agent

1. Create or open an **Agent** app in Dify.
2. In the **Tools** section, add your custom "MemU Dify Integration".
3. Add the tools `add_memory` and `search_memory`.
4. **Prompt Instructions**:
   Give your agent instructions on how to use memory. Example system prompt:

   > You have access to a long-term memory system called MemU.
   > - When the user shares important personal information, preferences, or facts, use the `add_memory` tool to save it.
   > - When answering questions about the user's past, preferences, or specific knowledge, first use `search_memory` to retrieve relevant context.
   > - Always check memory before saying "I don't know" about the user.

## troubleshooting

- **Connection Refused**: Ensure the Dify server can reach your MemU adapter. If using Docker or Cloud, `localhost` might not work. Use `host.docker.internal` or a public IP/tunnel.
- **Empty Results**: Ensure `user_id` matches. Dify sends a user ID; ensure you pass it correctly or use a fixed ID for testing.
