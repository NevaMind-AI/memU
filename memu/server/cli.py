#!/usr/bin/env python3
"""
MemU Server CLI

Command line interface for managing the MemU self-hosted server.
"""

import argparse
import os
import sys
from pathlib import Path

import uvicorn

from memu.config.server_config import get_settings


def start_server():
    """Start the MemU server (configuration via environment variables only)"""
    settings = get_settings()
    
    print(f"🚀 Starting MemU Server...")
    print(f"   Host: {settings.host}")
    print(f"   Port: {settings.port}")
    print(f"   Debug: {settings.debug}")
    print(f"   Memory Dir: {settings.memory_dir}")
    print(f"   LLM Provider: {settings.llm_provider}")
    print(f"   Embeddings: {settings.enable_embeddings}")
    print()
    
    # Validate LLM configuration
    if settings.llm_provider == "openai" and not settings.openai_api_key:
        print("❌ Error: OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        sys.exit(1)
    elif settings.llm_provider == "anthropic" and not settings.anthropic_api_key:
        print("❌ Error: Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable.")
        sys.exit(1)
    elif settings.llm_provider == "deepseek" and not settings.deepseek_api_key:
        print("❌ Error: DeepSeek API key is required. Set DEEPSEEK_API_KEY environment variable.")
        sys.exit(1)
    
    # Create memory directory if it doesn't exist
    memory_path = Path(settings.memory_dir)
    memory_path.mkdir(exist_ok=True)
    
    # Start server
    uvicorn.run(
        "memu.server.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )


def create_env_file():
    """Create a .env file from template"""
    env_path = Path(".env")
    example_path = Path(__file__).parent / ".env.example"
    
    if env_path.exists():
        print("❌ .env file already exists")
        return
    
    if not example_path.exists():
        print("❌ .env.example template not found")
        return
    
    # Copy template
    with open(example_path, 'r') as f:
        content = f.read()
    
    with open(env_path, 'w') as f:
        f.write(content)
    
    print("✅ Created .env file from template")
    print("   Please edit .env file and add your API keys")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="MemU Self-Hosted Server CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  memu-server start                   # Start server using .env variables
  memu-server init-env                 # Create .env file from template
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start command
    subparsers.add_parser("start", help="Start the server")
    
    # Init env command
    subparsers.add_parser("init-env", help="Create .env file from template")
    
    args = parser.parse_args()
    
    if args.command == "start":
        start_server()
    elif args.command == "init-env":
        create_env_file()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
