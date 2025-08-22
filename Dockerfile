# MemU Server Docker Image
FROM public.ecr.aws/docker/library/python:3.12-slim

# Build arguments for dependency selection
ARG INSTALL_MODE=server
ARG INCLUDE_GPU=false
ARG INCLUDE_LOCAL_MODELS=false

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    INSTALL_MODE=${INSTALL_MODE} \
    INCLUDE_GPU=${INCLUDE_GPU} \
    INCLUDE_LOCAL_MODELS=${INCLUDE_LOCAL_MODELS}

# Set working directory
WORKDIR /app

# Install system dependencies
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     curl \
#     && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml setup.cfg MANIFEST.in ./
COPY memu/ ./memu/
COPY docker-entrypoint.sh ./

# Make entrypoint script executable
RUN chmod +x docker-entrypoint.sh

# Create directories
RUN mkdir -p /app/memory /app/logs

# Create non-root user with home directory
RUN groupadd -r memu && useradd -r -g memu -m memu
RUN chown -R memu:memu /app
USER memu

# Add user's local bin to PATH
ENV PATH="/home/memu/.local/bin:$PATH"

# Install Python dependencies as non-root user based on build arguments
RUN pip install --user --upgrade pip

# Base installation (always install minimal dependencies)
RUN pip install --user -e "."

# Install additional dependencies based on build arguments
RUN if [ "$INSTALL_MODE" = "server" ] || [ "$INSTALL_MODE" = "all" ]; then \
        if [ "$INCLUDE_GPU" = "false" ]; then \
            pip install --user -e ".[server-cpu]"; \
        else \
            pip install --user -e ".[server]"; \
        fi; \
    fi

RUN if [ "$INSTALL_MODE" = "minimal" ]; then \
        pip install --user -e ".[minimal]"; \
    fi

RUN if [ "$INSTALL_MODE" = "llm" ] || [ "$INSTALL_MODE" = "all" ]; then \
        pip install --user -e ".[llm]"; \
    fi

RUN if [ "$INCLUDE_LOCAL_MODELS" = "true" ] && [ "$INCLUDE_GPU" = "false" ]; then \
        # Install CPU-only torch for local models without GPU support
        pip install --user torch --index-url https://download.pytorch.org/whl/cpu && \
        pip install --user transformers>=4.21.0 sentence-transformers>=2.2.0; \
    elif [ "$INCLUDE_LOCAL_MODELS" = "true" ] && [ "$INCLUDE_GPU" = "true" ]; then \
        # Install full local dependencies (including GPU support)
        pip install --user -e ".[local]"; \
    fi

RUN if [ "$INSTALL_MODE" = "dev" ]; then \
        pip install --user -e ".[dev]"; \
    fi

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"]

# Default command
CMD ["python", "-m", "memu.server.cli", "start"]
