#!/bin/bash
# MemU Server Docker Entrypoint

set -e

echo "🚀 Starting MemU Server in Docker..."
echo "======================================"

# Create memory directory if it doesn't exist
mkdir -p "${MEMU_MEMORY_DIR:-/app/memory}"

# Display configuration
echo "📊 Server Configuration:"
echo "   Host: ${MEMU_HOST:-0.0.0.0}"
echo "   Port: ${MEMU_PORT:-8000}"
echo "   Debug: ${MEMU_DEBUG:-false}"
echo "   Memory Dir: ${MEMU_MEMORY_DIR:-/app/memory}"
echo "   LLM Provider: ${MEMU_LLM_PROVIDER:-openai}"
echo "   Embeddings: ${MEMU_ENABLE_EMBEDDINGS:-true}"
echo ""

# Validate API keys based on provider
if [ "${MEMU_LLM_PROVIDER:-openai}" = "openai" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Error: OpenAI API key is required when using OpenAI provider"
    echo "   Please set OPENAI_API_KEY environment variable"
    exit 1
elif [ "${MEMU_LLM_PROVIDER}" = "anthropic" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Error: Anthropic API key is required when using Anthropic provider"
    echo "   Please set ANTHROPIC_API_KEY environment variable"
    exit 1
elif [ "${MEMU_LLM_PROVIDER}" = "deepseek" ] && [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "❌ Error: DeepSeek API key is required when using DeepSeek provider"
    echo "   Please set DEEPSEEK_API_KEY environment variable"
    exit 1
elif [ "${MEMU_LLM_PROVIDER}" = "azure" ] && ([ -z "$AZURE_API_KEY" ] || [ -z "$AZURE_ENDPOINT" ]); then
    echo "❌ Error: Azure API key and endpoint are required when using Azure provider"
    echo "   Please set AZURE_API_KEY and AZURE_ENDPOINT environment variables"
    exit 1
fi

echo "✅ Configuration validated"
echo ""
echo "🌐 Server will be available at:"
echo "   API: http://localhost:${MEMU_PORT:-8000}"
echo "   Docs: http://localhost:${MEMU_PORT:-8000}/docs"
echo "   Health: http://localhost:${MEMU_PORT:-8000}/health"
echo ""
echo "📝 Press Ctrl+C to stop the server"
echo ""

# Execute the command passed to the script or default to starting the server
exec "$@"
