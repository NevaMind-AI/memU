#!/usr/bin/env python3
"""
PersonaLab CLI - Command Line Interface for PersonaLab AI Framework

Usage:
    personalab --version
    personalab --help
    personalab info
    personalab test-connection [--api-url URL]
"""

import sys
import argparse
from typing import Optional
import json

from personalab import __version__


def print_info():
    """Print PersonaLab information"""
    info = {
        "name": "PersonaLab",
        "version": __version__,
        "description": "AI Memory and Conversation Management Framework",
        "homepage": "https://github.com/NevaMind-AI/PersonaLab",
        "documentation": "https://github.com/NevaMind-AI/PersonaLab#readme"
    }
    
    print("🤖 PersonaLab AI Framework")
    print("=" * 40)
    for key, value in info.items():
        print(f"{key.title()}: {value}")
    print("=" * 40)


def test_connection(api_url: Optional[str] = None):
    """Test connection to PersonaLab API"""
    if not api_url:
        api_url = "http://localhost:8000"
    
    try:
        import requests
        response = requests.get(f"{api_url}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Connection successful to {api_url}")
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Message: {data.get('message', 'No message')}")
        else:
            print(f"❌ Connection failed: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print(f"   Make sure PersonaLab API server is running at {api_url}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="PersonaLab AI Framework CLI",
        prog="personalab"
    )
    
    parser.add_argument(
        "--version", 
        action="version", 
        version=f"PersonaLab {__version__}"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Show PersonaLab information")
    
    # Test connection command
    test_parser = subparsers.add_parser("test-connection", help="Test API connection")
    test_parser.add_argument(
        "--api-url", 
        type=str, 
        default="http://localhost:8000",
        help="API URL to test (default: http://localhost:8000)"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.command == "info":
        print_info()
    elif args.command == "test-connection":
        test_connection(args.api_url)
    else:
        parser.print_help()


if __name__ == "__main__":
    main() 