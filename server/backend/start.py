#!/usr/bin/env python3
"""
Backend startup script for PersonaLab
"""

if __name__ == "__main__":
    import uvicorn
    from main import app
    
    print("🚀 Starting PersonaLab Backend Server...")
    print("📍 API Interface: http://localhost:8000")
print("📍 API Documentation: http://localhost:8000/docs")

uvicorn.run(app, host="0.0.0.0", port=8000, reload=False) 