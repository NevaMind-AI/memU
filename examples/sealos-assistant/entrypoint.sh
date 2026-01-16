#!/bin/bash
# Sealos DevBox entrypoint script
# This script is executed when deploying to production

set -e

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start the application
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
