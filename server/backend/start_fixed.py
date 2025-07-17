#!/usr/bin/env python3
"""
Backend startup script for MemU - Fixed Version
"""

if __name__ == "__main__":
    import uvicorn
    from main_fixed import app
    
    print("🚀 Starting MemU Backend Server (Fixed Version)...")
    print("📁 File-based Memory Management System")
    print("📍 API Interface: http://localhost:8000")
    print("📍 API Documentation: http://localhost:8000/docs")
    print("📍 Health Check: http://localhost:8000/api/health")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False) 