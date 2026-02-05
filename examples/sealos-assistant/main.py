"""
Personal AI Assistant with Long-Term Memory
Powered by MemU + FastAPI on Sealos DevBox

This example demonstrates how to build a memory-enabled AI assistant
that can be deployed on Sealos DevBox with 1-click deployment.

Usage:
    # Local development
    pip install -r requirements.txt
    python main.py

    # Or with uvicorn
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

# Add src to path for local development
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
if os.path.exists(src_path):
    sys.path.insert(0, src_path)

from memu.app import MemoryService

# Global memory service instance
memory_service: MemoryService | None = None


def get_llm_profiles() -> dict:
    """Build LLM profiles from environment variables."""
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
    """Initialize MemU memory service on startup."""
    global memory_service

    try:
        llm_profiles = get_llm_profiles()
        memory_service = MemoryService(llm_profiles=llm_profiles)
        print("✓ MemU Memory Service initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize MemU: {e}")
        raise

    yield

    print("Shutting down MemU Assistant...")


app = FastAPI(
    title="MemU Assistant",
    description="AI Assistant with Long-Term Memory powered by MemU",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    memories_used: int
    memories_stored: int


class MemorizeRequest(BaseModel):
    content: str
    user_id: str = "default"


class MemorizeResponse(BaseModel):
    status: str
    items_created: int
    categories: int


class RecallResponse(BaseModel):
    query: str
    memories_found: int
    memories: list[dict]


# API Endpoints
@app.get("/")
async def root():
    """Service information and available endpoints."""
    return {
        "service": "MemU Assistant",
        "description": "AI Assistant with Long-Term Memory",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "GET /": "This info",
            "GET /health": "Health check",
            "POST /chat": "Chat with memory-aware AI",
            "POST /memorize": "Store information in memory",
            "GET /recall": "Query stored memories",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "memory_service_initialized": memory_service is not None,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the AI assistant.

    The assistant will:
    1. Retrieve relevant memories from past conversations
    2. Use those memories as context for the response
    3. Store new information from the conversation
    """
    if not memory_service:
        raise HTTPException(status_code=503, detail="Memory service not initialized")

    try:
        # Retrieve relevant memories
        retrieve_result = await memory_service.retrieve(queries=[{"role": "user", "content": request.message}])

        memories = retrieve_result.get("items", [])

        # Build context from memories
        memory_context = []
        for mem in memories[:5]:
            if isinstance(mem, dict):
                summary = mem.get("summary", str(mem))
                memory_context.append(summary)

        # Generate response (in production, use full LLM with memory context)
        if memory_context:
            response_text = (
                f"Based on what I remember about you, here's my response to: '{request.message}'\n\n"
                f"Relevant context from our past conversations:\n"
                + "\n".join(f"- {ctx[:100]}..." if len(ctx) > 100 else f"- {ctx}" for ctx in memory_context)
            )
        else:
            response_text = f"I received your message: '{request.message}'. I don't have any relevant memories yet."

        # Store the conversation
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(f"User ({request.user_id}) said: {request.message}")
            temp_file = f.name

        try:
            memorize_result = await memory_service.memorize(
                resource_url=temp_file,
                modality="text",
            )
            memories_stored = len(memorize_result.get("items", []))
        finally:
            os.unlink(temp_file)

        return ChatResponse(
            response=response_text,
            memories_used=len(memories),
            memories_stored=memories_stored,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {e!s}")


@app.post("/memorize", response_model=MemorizeResponse)
async def memorize(request: MemorizeRequest):
    """Store information in long-term memory."""
    if not memory_service:
        raise HTTPException(status_code=503, detail="Memory service not initialized")

    try:
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(f"[User: {request.user_id}] {request.content}")
            temp_file = f.name

        try:
            result = await memory_service.memorize(
                resource_url=temp_file,
                modality="text",
            )
            return MemorizeResponse(
                status="stored",
                items_created=len(result.get("items", [])),
                categories=len(result.get("categories", [])),
            )
        finally:
            os.unlink(temp_file)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memorize failed: {e!s}")


@app.get("/recall", response_model=RecallResponse)
async def recall(query: str, limit: int = 5):
    """Recall memories related to a query."""
    if not memory_service:
        raise HTTPException(status_code=503, detail="Memory service not initialized")

    try:
        result = await memory_service.retrieve(queries=[{"role": "user", "content": query}])

        items = result.get("items", [])[:limit]
        memories = []
        for item in items:
            if isinstance(item, dict):
                memories.append({
                    "summary": item.get("summary", str(item)),
                    "category": item.get("category", "unknown"),
                })
            else:
                memories.append({"summary": str(item), "category": "unknown"})

        return RecallResponse(
            query=query,
            memories_found=len(memories),
            memories=memories,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recall failed: {e!s}")


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))

    print(f"Starting MemU Assistant on {host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True)
