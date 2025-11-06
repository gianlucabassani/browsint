#!/usr/bin/env python3
"""
Browsint Web Interface Runner
Simple script to start the web interface
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

if __name__ == "__main__":
    import uvicorn
    from app import app
    
    print("🚀 Starting Browsint Web Interface...")
    print("📍 Interface will be available at: http://127.0.0.1:8000")
    print("🔧 Press Ctrl+C to stop the server")
    
    try:
        uvicorn.run(
            app, 
            host="127.0.0.1", 
            port=8000, 
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Browsint Web Interface stopped")