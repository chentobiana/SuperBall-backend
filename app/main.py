from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.connection import connect_to_mongo, close_mongo_connection
from app.routes.auth import router as auth_router
from app.routes.matchmaking import router as matchmaking_router
from app.routes.game import router as game_router
from app.config import settings
import logging

# הגדרת logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# יצירת אפליקציית FastAPI
app = FastAPI(
    title="SuperBall Game Backend",
    description="Backend API למשחק SuperBall - מערכת הרשמה והתחברות",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# הגדרת CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # בפרודקשן צריך להגביל את זה לדומיינים ספציפיים
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# רישום routes
app.include_router(auth_router)
app.include_router(matchmaking_router)
app.include_router(game_router)


@app.on_event("startup")
async def startup_event():
    """אירוע שמתרחש בעת הפעלת השרת"""
    logger.info("Starting SuperBall Backend Server...")
    await connect_to_mongo()
    logger.info("Server started successfully!")


@app.on_event("shutdown")
async def shutdown_event():
    """אירוע שמתרחש בעת כיבוי השרת"""
    logger.info("Shutting down SuperBall Backend Server...")
    await close_mongo_connection()
    logger.info("Server shutdown complete!")


@app.get("/")
async def root():
    """נקודת כניסה בסיסית"""
    return {
        "message": "SuperBall Game Backend API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """בדיקת בריאות השרת"""
    return {
        "status": "healthy",
        "database": "connected"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info"
    )
