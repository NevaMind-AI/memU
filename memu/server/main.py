"""
MemU Self-Hosted Server Main Application

FastAPI application providing REST APIs for MemU memory management.
"""

import logging
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
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

# Get settings
settings = get_settings()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )


if __name__ == "__main__":
    start_server()
