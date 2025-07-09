# syntax=docker/dockerfile:1

# 1. Base image
FROM python:3.11-slim AS base

# 2. Set working directory
WORKDIR /app

# 3. Install system dependencies needed by psycopg2 & others
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy dependency definitions first (leverage Docker cache)
COPY server/backend/requirements.txt ./backend-requirements.txt
COPY requirements.txt ./root-requirements.txt

# 5. Install Python dependencies
RUN pip install --no-cache-dir -r backend-requirements.txt

# 6. Copy application code
COPY . .

# 7. Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 8. Expose API port
EXPOSE 8000

# 9. Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# 10. Default command (can be overridden at runtime)
CMD ["uvicorn", "server.backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"] 