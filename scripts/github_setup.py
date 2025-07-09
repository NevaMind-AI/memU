#!/usr/bin/env python3
"""
PersonaLab GitHub Setup Script

This script helps setup and publish PersonaLab to GitHub.

Usage:
    python scripts/github_setup.py --init     # Initialize Git repository
    python scripts/github_setup.py --commit   # Commit changes
    python scripts/github_setup.py --push     # Push to GitHub
    python scripts/github_setup.py --all      # Do all steps
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime


def run_command(cmd, check=True):
    """Run a shell command and return the result"""
    print(f"🔍 Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr and result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        
    if check and result.returncode != 0:
        sys.exit(1)
        
    return result


def check_git():
    """Check if git is available"""
    result = run_command("git --version", check=False)
    if result.returncode != 0:
        print("❌ Git is not installed or not available")
        print("💡 Please install Git: https://git-scm.com/downloads")
        sys.exit(1)
    print("✅ Git is available")


def init_repository():
    """Initialize Git repository if needed"""
    print("🚀 Initializing Git repository...")
    
    # Check if already a git repo
    if os.path.exists(".git"):
        print("✅ Git repository already exists")
        return
    
    # Initialize git repo
    run_command("git init")
    
    # Set main branch
    run_command("git branch -m main")
    
    print("✅ Git repository initialized")


def add_gitignore():
    """Ensure .gitignore is properly set up"""
    print("📝 Setting up .gitignore...")
    
    if os.path.exists(".gitignore"):
        print("✅ .gitignore already exists")
    else:
        print("⚠️  .gitignore not found - this might cause issues")
    
    # Add current changes
    run_command("git add .")


def commit_changes():
    """Commit all changes"""
    print("💾 Committing changes...")
    
    # Check if there are changes to commit
    result = run_command("git status --porcelain", check=False)
    if not result.stdout.strip():
        print("✅ No changes to commit")
        return
    
    # Add all files
    run_command("git add .")
    
    # Create commit message with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_message = f"PersonaLab v0.1.2 - Production ready release ({timestamp})"
    
    # Commit changes
    run_command(f'git commit -m "{commit_message}"')
    
    print("✅ Changes committed")


def setup_remote():
    """Setup GitHub remote"""
    print("🔗 Setting up GitHub remote...")
    
    # Check if remote already exists
    result = run_command("git remote -v", check=False)
    if "origin" in result.stdout:
        print("✅ Remote 'origin' already exists")
        print(result.stdout)
        return
    
    # Add remote (user needs to replace with their repo)
    github_url = "https://github.com/NevaMind-AI/PersonaLab.git"
    print(f"🔗 Adding remote: {github_url}")
    print("⚠️  Note: Update this URL to your GitHub repository!")
    
    run_command(f"git remote add origin {github_url}")
    print("✅ Remote added")


def push_to_github():
    """Push to GitHub"""
    print("🚀 Pushing to GitHub...")
    
    # Check if we have a remote
    result = run_command("git remote -v", check=False)
    if "origin" not in result.stdout:
        print("❌ No remote 'origin' found")
        print("💡 Add remote with: git remote add origin https://github.com/username/PersonaLab.git")
        return
    
    # Push to main branch
    run_command("git push -u origin main")
    
    print("✅ Pushed to GitHub")


def create_release_info():
    """Create release information"""
    print("📋 Creating release information...")
    
    release_info = f"""
# PersonaLab v0.1.2 Release

## 🎉 Release Information

- **Version**: 0.1.2
- **Date**: {datetime.now().strftime("%Y-%m-%d")}
- **Type**: Production Release

## 📦 Installation

```bash
pip install personalab
```

## 🔥 Key Features

- ✅ Stable PostgreSQL-based memory system
- ✅ Multi-LLM support (OpenAI, Anthropic, etc.)
- ✅ Advanced conversation management
- ✅ Vector-based semantic search
- ✅ CLI tools
- ✅ Full documentation

## 🚀 Quick Start

```python
from personalab import Persona

persona = Persona(agent_id="my_assistant")
response = persona.chat("Hello!", user_id="user_123")
print(response)
```

## 📚 Links

- 📖 Documentation: https://github.com/NevaMind-AI/PersonaLab#readme
- 🐛 Issues: https://github.com/NevaMind-AI/PersonaLab/issues
- 📦 PyPI: https://pypi.org/project/personalab/
"""
    
    with open("RELEASE_INFO.md", "w") as f:
        f.write(release_info)
    
    print("✅ Created RELEASE_INFO.md")


def main():
    parser = argparse.ArgumentParser(description="PersonaLab GitHub Setup Script")
    parser.add_argument("--init", action="store_true", help="Initialize Git repository")
    parser.add_argument("--commit", action="store_true", help="Commit changes")
    parser.add_argument("--push", action="store_true", help="Push to GitHub")
    parser.add_argument("--all", action="store_true", help="Do all steps")
    
    args = parser.parse_args()
    
    if not any([args.init, args.commit, args.push, args.all]):
        parser.print_help()
        return
    
    # Check we're in the right directory
    if not os.path.exists("pyproject.toml"):
        print("❌ Run this script from the project root directory")
        sys.exit(1)
    
    print("🤖 PersonaLab GitHub Setup Script")
    print("=" * 40)
    
    # Check git
    check_git()
    
    if args.init or args.all:
        init_repository()
        setup_remote()
        create_release_info()
    
    if args.commit or args.all:
        commit_changes()
    
    if args.push or args.all:
        push_to_github()
    
    print("🎉 GitHub setup completed!")
    print("💡 Next steps:")
    print("   1. Update GitHub remote URL if needed")
    print("   2. Create releases on GitHub")
    print("   3. Set up CI/CD workflows")


if __name__ == "__main__":
    main() 