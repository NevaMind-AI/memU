# MemU Server Docker Image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

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

# Install Python dependencies as non-root user
RUN pip install --user --upgrade pip && \
    pip install --user -e ".[server]"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"]

# Default command
CMD ["python", "-m", "memu.server.cli", "start", "--host", "0.0.0.0", "--port", "8000"]
