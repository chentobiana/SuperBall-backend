#!/usr/bin/env python3
"""
קובץ להפעלת שרת SuperBall Backend
"""

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print("🚀 Starting SuperBall Backend Server...")
    print(f"📍 Server will run on: http://{settings.HOST}:{settings.PORT}")
    print(f"📚 API Documentation: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"🗄️  Database: {settings.DATABASE_NAME}")
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info"
    )
