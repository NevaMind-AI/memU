"""
MemU Self-Hosted Server Main Application

FastAPI application providing REST APIs for MemU memory management.
"""

import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routers import memory
from .middleware import LoggingMiddleware

# Configure logging
from ..utils.logging import get_logger
logger = get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title="MemU Self-Hosted Server",
    description="Self-hosted server for MemU memory management system",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Read server config from environment
HOST = os.getenv("MEMU_HOST", "0.0.0.0")
PORT = int(os.getenv("MEMU_PORT", "8000"))
DEBUG = os.getenv("MEMU_DEBUG", "false").lower() == "true"

cors_origins_env = os.getenv("MEMU_CORS_ORIGINS", "*")
if cors_origins_env == "*":
    CORS_ORIGINS = ["*"]
else:
    CORS_ORIGINS = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Include routers
app.include_router(memory.router, prefix="/api/v1/memory", tags=["memory"])


@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "message": "MemU Self-Hosted Server",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "server": "memu-server",
        "version": "0.1.0"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Global exception handler caught: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc)
        }
    )


def start_server():
    """Start the server with uvicorn"""
    uvicorn.run(
        "memu.server.main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="info" if not DEBUG else "debug"
    )


if __name__ == "__main__":
    start_server()
