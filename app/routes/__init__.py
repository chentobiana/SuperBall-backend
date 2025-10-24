"""
Route handlers for the SuperBall game API endpoints.
"""

from .auth import router as auth_router
from .game import router as game_router
from .matchmaking import router as matchmaking_router
from .rewards import router as rewards_router
from .wheel import router as wheel_router

__all__ = [
    "auth_router",
    "game_router",
    "matchmaking_router",
    "rewards_router",
    "wheel_router"
]
