# Deploying MemU on Sealos DevBox

This guide demonstrates how to build and deploy a **Personal AI Assistant with Long-Term Memory** using MemU on [Sealos DevBox](https://sealos.io/products/devbox).

## Overview

MemU enables AI agents to maintain persistent, structured memory across conversations. Combined with Sealos DevBox's 1-click cloud development environment, you can quickly build and deploy memory-enabled AI applications.

**What we'll build:**
- A FastAPI-based AI assistant that remembers user preferences and past conversations
- Persistent memory storage using MemU's in-memory or PostgreSQL backend
- Simple REST API for chat interactions
- One-click deployment to production

**Time to complete:** ~15 minutes

## Prerequisites

- [Sealos account](https://sealos.io) (free tier available)
- OpenAI API key (or compatible provider like Nebius, Groq)

## Step 1: Create a DevBox Environment

1. Log in to [Sealos Dashboard](https://cloud.sealos.io)
2. Navigate to **DevBox** module
3. Click **Create New Project**
4. Select a **Python 3.12+** template
5. Configure resources (recommended: 2 vCPU, 4GB RAM)
6. Click **Create** - your environment will be ready in ~60 seconds

## Step 2: Connect Your IDE

1. In the DevBox project list, click the **VS Code** or **Cursor** button
2. Your local IDE will open with a secure SSH connection to the cloud environment
3. All code runs in the cloud, keeping your local machine free

## Step 3: Set Up the Project

Open the terminal in your connected IDE and run:

```bash
# Clone or create project directory
mkdir memu-assistant && cd memu-assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install memu-py fastapi uvicorn python-dotenv
```

## Step 4: Create the Application

Create the following files in your project:

### `.env`

```env
# LLM Provider Configuration
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1

# Or use Nebius (OpenAI-compatible)
# OPENAI_API_KEY=your_nebius_key
# OPENAI_BASE_URL=https://api.tokenfactory.nebius.com/v1/

# Model Configuration
CHAT_MODEL=gpt-4o-mini
EMBED_MODEL=text-embedding-3-small

# Memory Storage Configuration
MEMU_DATABASE_PROVIDER=inmemory
MEMU_DATABASE_DDL_MODE=create
# For SQLite persistence:
# MEMU_DATABASE_PROVIDER=sqlite
# MEMU_DATABASE_DSN=sqlite:///./data/memu.db
# For PostgreSQL persistence, install memu-py[postgres] and set:
# MEMU_DATABASE_PROVIDER=postgres
# MEMU_DATABASE_DSN=postgresql+psycopg://user:password@host:5432/memu

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

### `main.py`

```python
"""
Personal AI Assistant with Long-Term Memory
Powered by MemU + FastAPI on Sealos DevBox
"""

import os
from contextlib import asynccontextmanager
from typing import Annotated
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, StringConstraints

load_dotenv()

# MemU imports
from memu import MemoryService

# Global memory service
memory_service: MemoryService | None = None
SUPPORTED_DATABASE_PROVIDERS = ("inmemory", "sqlite", "postgres")
SUPPORTED_DATABASE_DDL_MODES = ("create", "validate")
NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def _env_choice(name: str, default: str, choices: tuple[str, ...]) -> str:
    value = (os.getenv(name, default) or default).strip().lower()
    if value not in choices:
        raise ValueError(f"{name} must be one of: {', '.join(choices)}")
    return value


def _env_value(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def get_database_config() -> dict:
    provider = _env_choice("MEMU_DATABASE_PROVIDER", "inmemory", SUPPORTED_DATABASE_PROVIDERS)
    ddl_mode = _env_choice("MEMU_DATABASE_DDL_MODE", "create", SUPPORTED_DATABASE_DDL_MODES)
    dsn = _env_value("MEMU_DATABASE_DSN")

    if provider == "postgres" and not dsn:
        raise ValueError("MEMU_DATABASE_DSN is required when MEMU_DATABASE_PROVIDER=postgres")

    metadata_store = {"provider": provider, "ddl_mode": ddl_mode}
    if dsn:
        metadata_store["dsn"] = dsn
    return {"metadata_store": metadata_store}


def get_llm_profiles() -> dict:
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    return {
        "default": {
            "provider": "openai",
            "base_url": base_url,
            "api_key": api_key,
            "chat_model": os.getenv("CHAT_MODEL", "gpt-4o-mini"),
            "client_backend": "sdk",
        },
        "embedding": {
            "provider": "openai",
            "base_url": base_url,
            "api_key": api_key,
            "embed_model": os.getenv("EMBED_MODEL", "text-embedding-3-small"),
            "client_backend": "sdk",
        },
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize MemU on startup."""
    global memory_service

    llm_profiles = get_llm_profiles()
    database_config = get_database_config()
    memory_service = MemoryService(llm_profiles=llm_profiles, database_config=database_config)
    provider = database_config["metadata_store"]["provider"]
    print(f"[OK] MemU Memory Service initialized (database: {provider})")
    yield
    print("Shutting down...")


app = FastAPI(
    title="MemU Assistant",
    description="AI Assistant with Long-Term Memory",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: NonEmptyString
    user_id: NonEmptyString = "default"


class ChatResponse(BaseModel):
    response: str
    memories_used: int
    memories_stored: int


class MemorizeRequest(BaseModel):
    content: NonEmptyString
    user_id: NonEmptyString = "default"


class MemorizeResponse(BaseModel):
    status: str
    items_created: int
    categories: int


class RecallResponse(BaseModel):
    query: str
    memories_found: int
    memories: list[dict]


@app.get("/")
async def root():
    return {
        "service": "MemU Assistant",
        "status": "running",
        "endpoints": ["/chat", "/memorize", "/recall", "/health"],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "memory_service": memory_service is not None}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the AI assistant. The assistant will:
    1. Retrieve relevant memories from past conversations
    2. Generate a response using those memories as context
    3. Store new information from the conversation
    """
    if not memory_service:
        raise HTTPException(status_code=503, detail="Memory service not initialized")

    # Step 1: Retrieve relevant memories
    retrieve_result = await memory_service.retrieve(
        queries=[{"role": "user", "content": request.message}],
        where={"user_id": request.user_id},
    )

    memories = retrieve_result.get("items", [])
    memories_context = ""
    if memories:
        memories_context = "\n\nRelevant memories from past conversations:\n"
        for mem in memories[:5]:  # Limit to top 5 memories
            if isinstance(mem, dict):
                memories_context += f"- {mem.get('summary', str(mem))}\n"

    # Step 2: Generate response (simplified - in production, use full LLM call)
    # For demo, we'll create a simple response acknowledging the memories
    response_text = f"I received your message: '{request.message}'"
    if memories:
        response_text += f"\n\nI found {len(memories)} relevant memories that might help."

    # Step 3: Store the conversation as a new memory
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(f"User ({request.user_id}): {request.message}")
        temp_file = f.name

    try:
        memorize_result = await memory_service.memorize(
            resource_url=temp_file,
            modality="document",
            user={"user_id": request.user_id},
        )
        memories_stored = len(memorize_result.get("items", []))
    finally:
        os.unlink(temp_file)

    return ChatResponse(
        response=response_text,
        memories_used=len(memories),
        memories_stored=memories_stored,
    )


@app.post("/memorize", response_model=MemorizeResponse)
async def memorize(request: MemorizeRequest):
    """Store information in long-term memory."""
    if not memory_service:
        raise HTTPException(status_code=503, detail="Memory service not initialized")

    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(request.content)
        temp_file = f.name

    try:
        result = await memory_service.memorize(
            resource_url=temp_file,
            modality="document",
            user={"user_id": request.user_id},
        )
        return MemorizeResponse(
            status="stored",
            items_created=len(result.get("items", [])),
            categories=len(result.get("categories", [])),
        )
    finally:
        os.unlink(temp_file)


@app.get("/recall", response_model=RecallResponse)
async def recall(
    query: NonEmptyString,
    user_id: NonEmptyString = "default",
    limit: int = Query(default=5, ge=1, le=20),
):
    """Recall memories related to a query."""
    if not memory_service:
        raise HTTPException(status_code=503, detail="Memory service not initialized")

    result = await memory_service.retrieve(
        queries=[{"role": "user", "content": query}],
        where={"user_id": user_id},
    )

    items = result.get("items", [])[:limit]
    memories = [
        {"summary": item.get("summary", str(item)) if isinstance(item, dict) else str(item)}
        for item in items
    ]
    return RecallResponse(query=query, memories_found=len(items), memories=memories)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )
```

### `requirements.txt`

```
memu-py>=1.5.1
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
python-dotenv>=1.0.0
```

### `requirements-postgres.txt`

Use this optional file when `MEMU_DATABASE_PROVIDER=postgres`:

```
-r requirements.txt
memu-py[postgres]>=1.5.1
```

### `entrypoint.sh`

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

exec uvicorn main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
```

## Step 5: Test Locally in DevBox

```bash
# Run the application
python main.py
```

Use the DevBox preview feature to access your running application, or test with curl:

```bash
# Health check
curl http://localhost:8000/health

# Store a memory
curl -X POST http://localhost:8000/memorize \
  -H "Content-Type: application/json" \
  -d '{"content": "User prefers dark mode and uses Python for AI development"}'

# Chat with memory
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What programming language do I use?"}'

# Recall memories
curl "http://localhost:8000/recall?query=programming%20preferences"
```

## Step 6: Deploy to Production

1. In the Sealos Dashboard, go to your DevBox project
2. Click **Create Release** to package your application
3. Click **Deploy** next to your release
4. Configure environment variables (OPENAI_API_KEY, etc.)
5. Click **Deploy** - your app will be live in minutes!

Your application will receive a public URL like: `https://your-app.cloud.sealos.io`

## Using with PostgreSQL (Optional)

For production deployments with persistent storage:

1. In Sealos Dashboard, go to **Database** module
2. Create a PostgreSQL instance
3. Install the Postgres dependency set:

```bash
pip install -r requirements-postgres.txt
```

   If you are not using the checked-in requirements files, install
   `pip install "memu-py[postgres]" fastapi uvicorn python-dotenv` instead.

4. Update your `.env` with the memU storage configuration:

```env
MEMU_DATABASE_PROVIDER=postgres
MEMU_DATABASE_DSN=postgresql+psycopg://user:password@host:5432/memu
MEMU_DATABASE_DDL_MODE=create
```

The same `MEMU_DATABASE_DSN` is used for metadata and pgvector-backed search
when `MEMU_DATABASE_PROVIDER=postgres`.

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info |
| `/health` | GET | Health check |
| `/chat` | POST | Chat with memory-aware AI |
| `/memorize` | POST | Store information in memory |
| `/recall` | GET | Query stored memories |

## Architecture

```
Sealos DevBox
  |
  +-- FastAPI application
      |
      +-- POST /chat
      |     retrieve memories -> compose response -> memorize turn
      |
      +-- POST /memorize
      |     write user-scoped content to memU
      |
      +-- GET /recall
            retrieve user-scoped memories

memU MemoryService
  |
  +-- LLM profiles
  |     default chat profile + embedding profile
  |
  +-- Storage
        inmemory by default
        sqlite with MEMU_DATABASE_PROVIDER=sqlite
        postgres + pgvector with MEMU_DATABASE_PROVIDER=postgres
```

## Benefits of This Setup

- **Zero Infrastructure Management**: Sealos handles Kubernetes complexity
- **Instant Environment**: Ready-to-code in 60 seconds
- **Persistent Memory**: MemU maintains context across sessions
- **Scalable**: Easily scale resources as needed
- **Cost-Effective**: Pay only for what you use

## Next Steps

- Add authentication for multi-user support
- Integrate with Slack, Discord, or other platforms
- Use PostgreSQL for production-grade persistence
- Add conversation history UI

## Resources

- [MemU Documentation](https://github.com/NevaMind-AI/MemU)
- [Sealos DevBox Guide](https://sealos.io/blog/how-to-setup-devbox)
- [FastAPI Documentation](https://fastapi.tiangolo.com)

---

*This guide was created for the MemU PR Hackathon - 2026 New Year Challenge (Issue #228)*

