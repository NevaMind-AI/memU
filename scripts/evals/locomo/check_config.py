#!/usr/bin/env python3
"""
Configuration Checker for LLM Clients

This script helps diagnose and fix configuration issues for both Azure OpenAI 
and DeepSeek clients that are causing 404 errors.
"""

import os
import sys
from pathlib import Path

import dotenv
dotenv.load_dotenv()

def check_azure_openai_config():
    """Check Azure OpenAI configuration"""
    print("=" * 50)
    print("AZURE OPENAI CONFIGURATION")
    print("=" * 50)
    
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    
    print(f"AZURE_OPENAI_ENDPOINT: {'✓ Set' if endpoint else '✗ Not set'}")
    if endpoint:
        print(f"  Value: {endpoint}")
    
    print(f"AZURE_OPENAI_API_KEY: {'✓ Set' if api_key else '✗ Not set'}")
    if api_key:
        print(f"  Value: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else api_key}")
    
    return bool(endpoint and api_key)

def check_deepseek_config():
    """Check DeepSeek configuration"""
    print("\n" + "=" * 50)
    print("DEEPSEEK CONFIGURATION")
    print("=" * 50)
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    endpoint = os.getenv("DEEPSEEK_ENDPOINT")
    
    print(f"DEEPSEEK_API_KEY: {'✓ Set' if api_key else '✗ Not set'}")
    if api_key:
        print(f"  Value: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else api_key}")
    
    print(f"DEEPSEEK_ENDPOINT: {'✓ Set' if endpoint else '✗ Not set'}")
    if endpoint:
        print(f"  Value: {endpoint}")
    else:
        print("  Suggested: https://api.deepseek.com")
    
    return bool(api_key and endpoint)

def check_deployment_name(deployment_name):
    """Check which client will be used for the given deployment"""
    print("\n" + "=" * 50)
    print("DEPLOYMENT ANALYSIS")
    print("=" * 50)
    
    print(f"Deployment name: {deployment_name}")
    
    is_deepseek = "deepseek" in deployment_name.lower()
    client_type = "DeepSeek" if is_deepseek else "Azure OpenAI"
    
    print(f"Will use: {client_type} client")
    
    if is_deepseek:
        print("Required environment variables:")
        print("  - DEEPSEEK_API_KEY")
        print("  - DEEPSEEK_ENDPOINT")
        return check_deepseek_config()
    else:
        print("Required environment variables:")
        print("  - AZURE_OPENAI_ENDPOINT")
        print("  - AZURE_OPENAI_API_KEY")
        return check_azure_openai_config()

def suggest_fixes():
    """Suggest fixes for common issues"""
    print("\n" + "=" * 50)
    print("TROUBLESHOOTING SUGGESTIONS")
    print("=" * 50)
    
    print("1. Create a .env file in the current directory with:")
    print("   # For DeepSeek:")
    print("   DEEPSEEK_API_KEY=your_deepseek_api_key_here")
    print("   DEEPSEEK_ENDPOINT=https://api.deepseek.com")
    print("")
    print("   # For Azure OpenAI:")
    print("   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/")
    print("   AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here")
    print("")
    print("2. If using DeepSeek, make sure you have:")
    print("   - Valid DeepSeek API key from https://platform.deepseek.com")
    print("   - Correct endpoint URL")
    print("")
    print("3. If using Azure OpenAI, make sure you have:")
    print("   - Valid Azure OpenAI resource and API key")
    print("   - Correct deployment name that exists in your Azure resource")
    print("   - Endpoint URL in format: https://your-resource.openai.azure.com/")
    print("")
    print("4. Check that your deployment name matches what you have configured:")
    print("   - DeepSeek models: should contain 'deepseek' in the name")
    print("   - Azure OpenAI models: should match your Azure deployment name")

def main():
    """Main configuration checker"""
    print("LLM CLIENT CONFIGURATION CHECKER")
    print("This script helps diagnose 404 and configuration errors\n")
    
    # Check current directory for .env file
    env_file = Path(".env")
    print(f".env file: {'✓ Found' if env_file.exists() else '✗ Not found'}")
    if env_file.exists():
        print(f"  Location: {env_file.absolute()}")
    
    # Get deployment name from command line or use default
    deployment_name = sys.argv[1] if len(sys.argv) > 1 else "DeepSeek-V3-0324"
    
    # Check configuration for the deployment
    config_ok = check_deployment_name(deployment_name)
    
    # Show overall status
    print("\n" + "=" * 50)
    print("OVERALL STATUS")
    print("=" * 50)
    
    if config_ok:
        print("✓ Configuration looks good!")
        print("If you're still getting 404 errors, check:")
        print("  1. API key validity")
        print("  2. Endpoint URL correctness")
        print("  3. Deployment name exists in your service")
    else:
        print("✗ Configuration issues detected")
        suggest_fixes()

if __name__ == "__main__":
    main() 