#!/usr/bin/env python3
"""
Setup script for PersonaLab .env configuration

This script helps users set up their .env file for API keys and configuration.
"""

import os
from pathlib import Path
from personalab.config import setup_env_file, config


def main():
    """Main setup function"""
    
    print("=== PersonaLab Environment Setup ===\n")
    
    # Check current directory
    current_dir = Path.cwd()
    print(f"Current directory: {current_dir}")
    
    # Check for .env files
    env_file = current_dir / ".env"
    example_file = current_dir / ".env.example"
    
    print(f".env file exists: {env_file.exists()}")
    print(f".env.example exists: {example_file.exists()}")
    print()
    
    # Setup .env file
    if not env_file.exists():
        if example_file.exists():
            print("Setting up .env file from template...")
            setup_env_file()
        else:
            print("Creating basic .env file...")
            env_content = """# PersonaLab Environment Configuration
# Add your API keys here

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo

# Pipeline Configuration  
DEFAULT_TEMPERATURE=0.3
DEFAULT_MAX_TOKENS=2000
"""
            env_file.write_text(env_content)
            print("✓ Created basic .env file")
    else:
        print("✓ .env file already exists")
    
    print()
    
    # Test configuration
    print("=== Testing Configuration ===")
    
    # Reload config to pick up any new .env file
    from personalab.config import Config
    test_config = Config()
    
    print(f"OpenAI API Key configured: {bool(test_config.openai_api_key)}")
    if test_config.openai_api_key:
        masked_key = test_config.openai_api_key[:8] + "..." + test_config.openai_api_key[-4:]
        print(f"API Key: {masked_key}")
    else:
        print("❌ No OpenAI API key found")
    
    print(f"Model: {test_config.openai_model}")
    print(f"Temperature: {test_config.default_temperature}")
    print(f"Max Tokens: {test_config.default_max_tokens}")
    
    print()
    
    # Configuration validation
    if test_config.validate_llm_config("openai"):
        print("✅ OpenAI configuration is valid!")
        print("You can now run the examples with LLM support")
    else:
        print("⚠️  OpenAI configuration is incomplete")
        print("📝 Next steps:")
        print(f"   1. Edit {env_file}")
        print("   2. Replace 'your_openai_api_key_here' with your actual API key")
        print("   3. Save the file and run this script again")
    
    print()
    print("=== Quick Test ===")
    print("Run: python example_memory_update.py")


if __name__ == "__main__":
    main() 