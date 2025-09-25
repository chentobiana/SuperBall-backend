import random
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel
from typing import Dict
from app.models.game import MoveRequest, MoveResponse, GameSession
from app.services.game_service import GameService
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/game", tags=["game"])



# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, game_id: str):
        await websocket.accept()
        self.active_connections[game_id] = websocket

    def disconnect(self, game_id: str):
        if game_id in self.active_connections:
            del self.active_connections[game_id]

    async def send_personal_message(self, message: dict, game_id: str):
        if game_id in self.active_connections:
            try:
                await self.active_connections[game_id].send_text(json.dumps(message))
            except Exception:
                # Connection might be closed
                self.disconnect(game_id)



manager = ConnectionManager()


def get_game_service():
    return GameService()


class InitialBoardResponse(BaseModel):
    finalBoard: list[list[str]]


class BombMoveRequest(BaseModel):
    x: int
    y: int
    game_id: str
    player_uniq_id: str


COLORS = [
    "Purple",
    "Green",
    "Blue",
    "Yellow",
    "Red",
    "Pink",
]


def generate_board(rows: int = 8, cols: int = 7) -> list[list[str]]:
    return [[random.choice(COLORS) for _ in range(cols)] for _ in range(rows)]


@router.get("/initial-board", response_model=InitialBoardResponse)
async def get_initial_board() -> InitialBoardResponse:
    board = generate_board(8, 7)
    return InitialBoardResponse(finalBoard=board)


@router.get("/game-info/{game_id}")
async def get_game_info(
    game_id: str,
    game_service: GameService = Depends(get_game_service)
):
    """Get game information including player IDs"""
    try:
        game = await game_service.game_repo.find_by_id(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        
        return {
            "game_id": game_id,
            "player1_id": game.player1_id,
            "player2_id": game.player2_id,
            "player1_name": game.player1_name,
            "player2_name": game.player2_name,
            "current_player_id": game.current_player_id,
            "status": game.status,
            "round": game.round
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Game creation is now handled by matchmaking service
# Use /matchmaking/join to find opponents and create games automatically


@router.post("/move", response_model=MoveResponse)
async def make_move(
    request: MoveRequest,
    game_service: GameService = Depends(get_game_service)
):
    """Make a move in the game"""
    try:
        response = await game_service.make_move(
            request.game_id,
            request.player_uniq_id,
            request.x,
            request.y
        )

        # Notify other player via WebSocket
        await manager.send_personal_message({
            "type": "opponent_move",
            "data": response.model_dump()
        }, request.game_id)

        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error making move: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bomb", response_model=MoveResponse)
async def use_bomb(
    request: BombMoveRequest,
    game_service: GameService = Depends(get_game_service)
):
    """Use a bomb at the specified position"""
    try:
        response = await game_service.use_bomb(
            request.game_id,
            request.player_uniq_id,
            request.x,
            request.y
        )

        # Notify other player via WebSocket
        await manager.send_personal_message({
            "type": "opponent_bomb",
            "data": response.model_dump()
        }, request.game_id)

        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error using bomb: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/state/{game_id}")
async def get_game_state(
    game_id: str,
    game_service: GameService = Depends(get_game_service)
):
    """Get current game state"""
    try:
        game = await game_service.get_game_state(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        return game
    except Exception as e:
        logger.error(f"Error getting game state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/player/{player_id}/games")
async def get_player_games(
    player_id: str,
    game_service: GameService = Depends(get_game_service)
):
    """Get all active games for a player"""
    try:
        games = await game_service.get_player_games(player_id)
        return games
    except Exception as e:
        logger.error(f"Error getting player games: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    """WebSocket endpoint for real-time game updates"""
    await manager.connect(websocket, game_id)
    try:
        while True:
            # Keep connection alive, wait for messages
            data = await websocket.receive_text()
            # Echo back for now - can be extended for chat or other features
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(game_id)
