#!/bin/bash

# PersonaLab API Server Startup Script
# This script starts the PersonaLab server using Docker Compose

set -e

echo "🚀 Starting PersonaLab API Server"
echo "=================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Navigate to project root
cd "$(dirname "$0")/.."

echo "📍 Current directory: $(pwd)"

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml not found. Make sure you're in the PersonaLab project directory."
    exit 1
fi

# Set default environment variables if not set
export OPENAI_API_KEY=${OPENAI_API_KEY:-""}

echo "🔧 Configuration:"
echo "   - API Port: 8000"
echo "   - Database Port: 5432" 
echo "   - OpenAI API Key: ${OPENAI_API_KEY:+Set}"

# Start services
echo ""
echo "🐳 Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services started successfully!"
    echo ""
    echo "🌐 API Server: http://localhost:8000"
    echo "📚 API Docs: http://localhost:8000/docs"
    echo "🗄️ Database: localhost:5432"
    echo ""
    echo "📋 To check status: docker-compose ps"
    echo "📜 To view logs: docker-compose logs -f backend"
    echo "🛑 To stop: docker-compose down"
    echo ""
    echo "📝 Run the example:"
    echo "   cd examples && python remote_api_example.py"
else
    echo "❌ Failed to start services. Check logs:"
    docker-compose logs
    exit 1
fi 