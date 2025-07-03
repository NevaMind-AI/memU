#!/usr/bin/env python3
"""
PersonaLab Backend Management System - FastAPI Backend Startup Script
"""

import os
import sys
import subprocess
import psycopg2
from pathlib import Path

# Add project root directory to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def print_banner():
    """Print startup banner"""
    print("=" * 50)
    print("🚀 PersonaLab Backend Management System (FastAPI)")
    print("=" * 50)

def check_environment():
    """Check runtime environment"""
    print("🔍 Checking runtime environment...")
    
    # Check Python version
    python_version = sys.version
    print(f"✅ Python version: {python_version}")
    
    # Check dependencies
    required_packages = ['fastapi', 'uvicorn', 'psycopg2', 'pgvector']
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}: installed")
        except ImportError:
            print(f"❌ {package}: not installed")
            print(f"💡 Please run: pip install {package}")
            return False
    
    return True

def check_database():
    """Check database connection"""
    print("\n🔍 Checking database configuration...")
    
    db_config = {
        'POSTGRES_HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'POSTGRES_PORT': os.getenv('POSTGRES_PORT', '5432'),
        'POSTGRES_DB': os.getenv('POSTGRES_DB', 'personalab'),
        'POSTGRES_USER': os.getenv('POSTGRES_USER', 'chenhong'),
        'POSTGRES_PASSWORD': os.getenv('POSTGRES_PASSWORD', '')
    }
    
    print("📋 Database configuration:")
    for key, value in db_config.items():
        if 'PASSWORD' in key:
            print(f"   {key}: {'*' * len(value)}")
        else:
            print(f"   {key}: {value}")
    
    # Test database connection
    try:
        connection_string = f"postgresql://{db_config['POSTGRES_USER']}:{db_config['POSTGRES_PASSWORD']}@{db_config['POSTGRES_HOST']}:{db_config['POSTGRES_PORT']}/{db_config['POSTGRES_DB']}"
        
        with psycopg2.connect(connection_string) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        
        print("✅ Database connection successful")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("💡 Please check:")
        print("   1. PostgreSQL service is running")
        print("   2. Database configuration is correct")
        print("   3. Network connection is normal")
        
        print("\n⚠️  Database connection failed, but will still try to start server")
        print("   (Some features may not work properly)")
        return False

def main():
    """Main function"""
    print_banner()
    
    # Check environment
    if not check_environment():
        print("\n❌ Environment check failed, please install missing dependencies")
        return 1
    
    # Check database
    check_database()
    
    print("\n🚀 Starting FastAPI server...")
    print("📍 API documentation: http://localhost:8080/docs")
    print("📍 API endpoint: http://localhost:8080")
    print("🔧 Press Ctrl+C to stop server")
    
    try:
        # Start FastAPI server
        import uvicorn
        uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
        return 0
    except Exception as e:
        print(f"\n❌ Startup failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 