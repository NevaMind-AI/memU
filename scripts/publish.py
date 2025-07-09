#!/usr/bin/env python3
"""
PersonaLab Publishing Script

This script helps automate the process of publishing PersonaLab to PyPI.

Usage:
    python scripts/publish.py --test    # Publish to test PyPI
    python scripts/publish.py --prod    # Publish to production PyPI
    python scripts/publish.py --check   # Just check the build
"""

import os
import sys
import subprocess
import argparse
import shutil
from pathlib import Path


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


def clean_build():
    """Clean build directories"""
    print("🧹 Cleaning build directories...")
    
    dirs_to_clean = ['build', 'dist', 'personalab.egg-info']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"   Removed {dir_name}/")
    
    print("✅ Build directories cleaned")


def build_package():
    """Build the package"""
    print("📦 Building package...")
    
    # Build the package
    result = run_command("python -m build")
    
    if os.path.exists("dist"):
        files = os.listdir("dist")
        print(f"✅ Built {len(files)} files:")
        for file in files:
            print(f"   📄 {file}")
    else:
        print("❌ No dist directory found")
        sys.exit(1)


def check_package():
    """Check the package with twine"""
    print("🔍 Checking package...")
    
    run_command("python -m twine check dist/*")
    print("✅ Package check passed")


def upload_to_test_pypi():
    """Upload to test PyPI"""
    print("🚀 Uploading to Test PyPI...")
    
    run_command("python -m twine upload --repository testpypi dist/*")
    print("✅ Uploaded to Test PyPI")
    print("📋 Test installation: pip install --index-url https://test.pypi.org/simple/ personalab")


def upload_to_pypi():
    """Upload to production PyPI"""
    print("🚀 Uploading to PyPI...")
    
    # Confirm production upload
    response = input("⚠️  Are you sure you want to upload to PRODUCTION PyPI? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Upload cancelled")
        return
    
    run_command("python -m twine upload dist/*")
    print("✅ Uploaded to PyPI")
    print("📋 Installation: pip install personalab")


def check_requirements():
    """Check if required tools are installed"""
    print("🔍 Checking requirements...")
    
    required_tools = ['build', 'twine']
    missing_tools = []
    
    for tool in required_tools:
        result = run_command(f"python -m {tool} --version", check=False)
        if result.returncode != 0:
            missing_tools.append(tool)
    
    if missing_tools:
        print(f"❌ Missing tools: {', '.join(missing_tools)}")
        print("💡 Install with: pip install build twine")
        sys.exit(1)
    
    print("✅ All requirements satisfied")


def main():
    parser = argparse.ArgumentParser(description="PersonaLab Publishing Script")
    parser.add_argument("--test", action="store_true", help="Publish to test PyPI")
    parser.add_argument("--prod", action="store_true", help="Publish to production PyPI")
    parser.add_argument("--check", action="store_true", help="Just build and check")
    
    args = parser.parse_args()
    
    if not any([args.test, args.prod, args.check]):
        parser.print_help()
        return
    
    # Check we're in the right directory
    if not os.path.exists("pyproject.toml"):
        print("❌ Run this script from the project root directory")
        sys.exit(1)
    
    print("🤖 PersonaLab Publishing Script")
    print("=" * 40)
    
    # Check requirements
    check_requirements()
    
    # Clean build
    clean_build()
    
    # Build package
    build_package()
    
    # Check package
    check_package()
    
    if args.check:
        print("✅ Build and check completed successfully!")
        return
    
    if args.test:
        upload_to_test_pypi()
    elif args.prod:
        upload_to_pypi()
    
    print("🎉 Publishing completed!")


if __name__ == "__main__":
    main() 