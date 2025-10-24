"""
Main application module for the SuperBall game backend.
Configures FastAPI application, middleware, routes, and event handlers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.connection import connect_to_mongo, close_mongo_connection
from app.routes.auth import router as auth_router
from app.routes.matchmaking import router as matchmaking_router
from app.routes.game import router as game_router
from app.routes.rewards import router as rewards_router
from app.routes.wheel import router as wheel_router
from app.config import settings
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="SuperBall Game Backend",
    description="SuperBall Game Backend API - Authentication and Game Services",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route handlers
app.include_router(auth_router)
app.include_router(matchmaking_router)
app.include_router(game_router)
app.include_router(rewards_router)
app.include_router(wheel_router)


@app.on_event("startup")
async def startup_event():
    """Initialize server resources and establish database connection."""
    logger.info("Starting SuperBall Backend Server...")
    await connect_to_mongo()
    logger.info("Server started successfully!")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources and close database connection on server shutdown."""
    logger.info("Shutting down SuperBall Backend Server...")
    await close_mongo_connection()
    logger.info("Server shutdown complete!")


@app.get("/")
async def root():
    """Root endpoint providing basic API information."""
    return {
        "message": "SuperBall Game Backend API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring service status."""
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
