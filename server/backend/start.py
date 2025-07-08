#!/usr/bin/env python3
"""
Backend startup script for PersonaLab
"""

if __name__ == "__main__":
    import uvicorn
    from main import app
    
    print("🚀 Starting PersonaLab Backend Server...")
    print("📍 API Interface: http://localhost:8080")
    print("📍 API Documentation: http://localhost:8080/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=False) 