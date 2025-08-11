#!/bin/bash

# MemU Server Quick Start Script

echo "🚀 MemU Self-Hosted Server Quick Start"
echo "======================================"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp memu/server/env.example .env
    echo "✅ Created .env file"
    echo "⚠️  Please edit .env file and add your API keys before starting the server"
    echo ""
    echo "Required environment variables:"
    echo "  - OPENAI_API_KEY (for OpenAI)"
    echo "  - ANTHROPIC_API_KEY (for Anthropic)"  
    echo "  - DEEPSEEK_API_KEY (for DeepSeek)"
    echo ""
    echo "Edit .env file and run this script again."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing server dependencies..."
pip install -e ".[server]"

# Create memory directory
echo "📁 Creating memory directory..."
mkdir -p memory

# Start server
echo "🚀 Starting MemU server..."
echo "   Server will be available at: http://localhost:8000"
echo "   API documentation: http://localhost:8000/docs"
echo "   Press Ctrl+C to stop the server"
echo ""

python -m memu.server.cli start
