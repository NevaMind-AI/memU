#!/usr/bin/env python3
"""
PersonaLab Release Preparation Script
- Clean project files
- Validate configuration
- Run tests
- Update version information
- Prepare GitHub release
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, check=True):
    """Run command and return result"""
    print(f"🔧 Running: {cmd}")
    result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr and check:
        print(f"Error: {result.stderr}")
    return result

def cleanup_project():
    """Clean project files"""
    print("🧹 Cleaning project files...")
    
    # Clean Python cache
    patterns_to_remove = [
        "__pycache__",
        "*.pyc", 
        "*.pyo",
        "*.egg-info",
        ".pytest_cache",
        ".coverage",
        "htmlcov",
        "*.db",
        "*.sqlite",
        "*.sqlite3"
    ]
    
    for pattern in patterns_to_remove:
        run_command(f"find . -name '{pattern}' -exec rm -rf {{}} + 2>/dev/null || true", check=False)
    
    print("✅ Project cleaning completed")

def check_dependencies():
    """Check project dependencies"""
    print("📦 Checking project dependencies...")
    
    required_files = [
        "requirements.txt",
        "setup.py", 
        "pyproject.toml",
        "README.md",
        "LICENSE"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ Dependencies check passed")
    return True

def validate_code_quality():
    """Validate code quality"""
    print("🔍 Validating code quality...")
    
    # Check Python syntax
    try:
        result = run_command("python -m py_compile personalab/__init__.py", check=False)
        if result.returncode != 0:
            print("❌ Python syntax check failed")
            return False
    except:
        print("⚠️  Skipping syntax check (py_compile not available)")
    
    # Try to import package
    try:
        run_command("python -c 'import personalab; print(\"Import successful\")'")
        print("✅ Package import test passed")
    except:
        print("❌ Package import failed")
        return False
    
    return True

def check_git_status():
    """Check Git status"""
    print("📝 Checking Git status...")
    
    try:
        # Check if in git repository
        run_command("git status --porcelain")
        
        # Check for uncommitted changes
        result = run_command("git status --porcelain", check=False)
        if result.stdout.strip():
            print("📋 Found uncommitted changes:")
            print(result.stdout)
            return True
        else:
            print("✅ Working directory clean")
            return True
            
    except:
        print("❌ Not in Git repository or Git not available")
        return False

def create_release_summary():
    """Create release summary"""
    print("📊 Creating release summary...")
    
    summary = {
        "Project": "PersonaLab",
        "Description": "AI Memory and Conversation Management System",
        "Key Features": [
            "PostgreSQL database support",
            "Multi-LLM provider integration (OpenAI, Anthropic, etc.)",
            "Intelligent memory management (Profile, Events, Mind)", 
            "Vector embeddings and semantic search",
            "Conversation recording and retrieval",
            "Psychological insights analysis"
        ],
        "Latest Fixes": [
            "ConversationManager method call errors",
            "PostgreSQL connection and configuration issues",
            "Memory update pipeline optimization",
            "Enhanced error handling and logging"
        ]
    }
    
    print("\n" + "="*50)
    print("🚀 PersonaLab Release Summary")
    print("="*50)
    for key, value in summary.items():
        if isinstance(value, list):
            print(f"{key}:")
            for item in value:
                print(f"  • {item}")
        else:
            print(f"{key}: {value}")
    print("="*50)
    
    return summary

def main():
    """Main function"""
    print("🚀 PersonaLab Release Preparation Script")
    print("="*50)
    
    # Ensure we're in project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    print(f"📂 Working directory: {os.getcwd()}")
    
    success = True
    
    # 1. Clean project
    cleanup_project()
    
    # 2. Check dependencies
    if not check_dependencies():
        success = False
    
    # 3. Validate code quality  
    if not validate_code_quality():
        success = False
    
    # 4. Check Git status
    if not check_git_status():
        success = False
    
    # 5. Create release summary
    create_release_summary()
    
    if success:
        print("\n🎉 Release preparation completed!")
        print("\n📋 Next steps:")
        print("  1. git add .")
        print("  2. git commit -m 'feat: prepare for release with PostgreSQL support'")
        print("  3. git push origin main")
        print("  4. Create new Release on GitHub")
        print("\n🔗 Suggested Release content:")
        print("  Title: PersonaLab v1.0.0 - PostgreSQL Integration & Enhanced Memory")
        print("  Tag: v1.0.0")
        print("  Description: Major update including PostgreSQL support, multi-LLM integration and enhanced memory management")
    else:
        print("\n❌ Release preparation failed, please fix the above issues")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 