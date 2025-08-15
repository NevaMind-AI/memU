#!/usr/bin/env python3
"""
MemU Server CLI

Command line interface for managing the MemU self-hosted server.
"""

import argparse
import os
import sys
import uvicorn
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def _get_bool_env(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).lower() == "true"


def start_server():
    """Start the MemU server (configuration via environment variables only)"""
    host = os.getenv("MEMU_HOST", "0.0.0.0")
    port = int(os.getenv("MEMU_PORT", "8000"))
    debug = _get_bool_env("MEMU_DEBUG", False)
    memory_dir = os.getenv("MEMU_MEMORY_DIR", "memu/server/memory")
    llm_provider = os.getenv("MEMU_LLM_PROVIDER", "openai").lower()
    enable_embeddings = _get_bool_env("MEMU_ENABLE_EMBEDDINGS", True)

    print(f"🚀 Starting MemU Server...")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Debug: {debug}")
    print(f"   Memory Dir: {memory_dir}")
    print(f"   LLM Provider: {llm_provider}")
    print(f"   Embeddings: {enable_embeddings}")
    print()
    
    # Validate LLM configuration
    if llm_provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        sys.exit(1)
    elif llm_provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable.")
        sys.exit(1)
    elif llm_provider == "deepseek" and not os.getenv("DEEPSEEK_API_KEY"):
        print("❌ Error: DeepSeek API key is required. Set DEEPSEEK_API_KEY environment variable.")
        sys.exit(1)
    elif llm_provider == "openrouter" and not os.getenv("OPENROUTER_API_KEY"):
        print(
            "❌ Error: OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable."
        )
        sys.exit(1)

    elif llm_provider == "azure":
        missing = []
        if not os.getenv("AZURE_API_KEY"):
            missing.append("AZURE_API_KEY")
        if not os.getenv("AZURE_ENDPOINT"):
            missing.append("AZURE_ENDPOINT")
        # Deployment name is required by Azure for the model parameter
        if not os.getenv("MEMU_AZURE_DEPLOYMENT_NAME"):
            missing.append("MEMU_AZURE_DEPLOYMENT_NAME")
        if missing:
            print(f"❌ Error: Azure OpenAI requires {', '.join(missing)}. Set them in environment variables.")
            sys.exit(1)
    
    # Create memory directory if it doesn't exist
    memory_path = Path(memory_dir)
    memory_path.mkdir(exist_ok=True)
    
    # Start server
    uvicorn.run(
        "memu.server.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
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
