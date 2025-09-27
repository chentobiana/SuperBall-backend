import random
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel
from typing import Dict, List
from app.models.game import MoveRequest, MoveResponse, GameSession
from app.services.game_service import GameService
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/game", tags=["game"])



# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, game_id: str):
        await websocket.accept()
        self.active_connections.setdefault(game_id, []).append(websocket)
        logger.info(f"[WS] Player connected to game {game_id}. Total connections: {len(self.active_connections[game_id])}")

    def disconnect(self, game_id: str):
        if game_id in self.active_connections:
            sockets = [ws for ws in self.active_connections[game_id] if not ws.client_state.name == "DISCONNECTED"]
            before = len(self.active_connections[game_id])
            if sockets:
                self.active_connections[game_id] = sockets
                after = len(sockets)
                logger.info(f"[WS] Disconnected sockets cleaned for {game_id}. Before={before}, After={after}")
            else:
                del self.active_connections[game_id]
                logger.info(f"[WS] All sockets disconnected from game {game_id}")

    async def send_personal_message(self, message: dict, game_id: str):
        """שולח הודעה לכל השחקנים המחוברים ל־game_id"""
        if game_id in self.active_connections:
            dead: List[WebSocket] = []
            for ws in list(self.active_connections[game_id]):
                try:
                    await ws.send_text(json.dumps(message))
                    logger.info(f"[WS] Sent message to game {game_id}: {message['type']}")
                except Exception as e:
                    logger.error(f"[WS] Failed to send to client in {game_id}: {e}")
                    dead.append(ws)
            # Cleanup
            if dead:
                self.active_connections[game_id] = [ws for ws in self.active_connections[game_id] if ws not in dead]
                if not self.active_connections[game_id]:
                    del self.active_connections[game_id]
                logger.info(f"[WS] Cleaned up {len(dead)} dead sockets for game {game_id}")




manager = ConnectionManager()


def get_game_service():
    return GameService()


class BombMoveRequest(BaseModel):
    x: int
    y: int
    game_id: str
    uniqId: str


## Note: Removed UX-only /initial-board. Clients should call /game/state/{game_id}.


# Game creation is now handled by matchmaking service over WebSocket


@router.post("/move", response_model=MoveResponse)
async def make_move(
    request: MoveRequest,
    game_service: GameService = Depends(get_game_service)
):
    """Make a move in the game"""
    try:
        response = await game_service.make_move(
            request.game_id,
            request.uniqId,
            request.x,
            request.y
        )

        # Notify all players via WebSocket about the move and current turn
        await manager.send_personal_message({
            "type": "opponent_move",
            "data": response.model_dump()
        }, request.game_id)
        
        # Also send turn update
        game = await game_service.get_game_state(request.game_id)
        if game:
            await manager.send_personal_message({
                "type": "turn_update",
                "current_player_id": game.current_player_id,
                "current_player_name": game.player1_name if game.current_player_id == game.player1_id else game.player2_name,
                "round": game.round,
                "player1_moves_left": game.player1_moves_left,
                "player2_moves_left": game.player2_moves_left
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
            request.uniqId,
            request.x,
            request.y
        )

        # Notify all players via WebSocket about the bomb and current turn
        await manager.send_personal_message({
            "type": "opponent_bomb",
            "data": response.model_dump()
        }, request.game_id)
        
        # Also send turn update
        game = await game_service.get_game_state(request.game_id)
        if game:
            await manager.send_personal_message({
                "type": "turn_update",
                "current_player_id": game.current_player_id,
                "current_player_name": game.player1_name if game.current_player_id == game.player1_id else game.player2_name,
                "round": game.round,
                "player1_moves_left": game.player1_moves_left,
                "player2_moves_left": game.player2_moves_left
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
    """Get current game state in structured format"""
    try:
        game = await game_service.get_game_state(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        
        # Pull rules from settings (with defaults)
        try:
            from app.config import settings
            total_rounds = int(getattr(settings, "TOTAL_ROUNDS", 5))
            turns_per_round = int(getattr(settings, "TURNS_PER_ROUND", 2))
            turn_seconds = int(getattr(settings, "TURN_SECONDS", 30))
        except Exception:
            total_rounds, turns_per_round, turn_seconds = 5, 2, 30

        return {
            "game_id": game_id,
            "player1_id": game.player1_id,
            "player2_id": game.player2_id,
            "player1_name": game.player1_name,
            "player2_name": game.player2_name,
            "current_player_id": game.current_player_id,
            "status": game.status,
            "round": game.round,
            "rules": {
                "total_rounds": total_rounds,
                "turns_per_round": turns_per_round,
                "turn_seconds": turn_seconds,
            },
            "current_turn_deadline": game.current_turn_deadline,
            "board": game.board,
            "player1": {
                "score": game.player1_score,
                "moves_left": game.player1_moves_left,
                "bombs": game.player1_bombs,
            },
            "player2": {
                "score": game.player2_score,
                "moves_left": game.player2_moves_left,
                "bombs": game.player2_bombs,
            },
        }
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
            try:
                # Try to parse incoming message
                message = json.loads(data)
                logger.info(f"[WS] Received message in game {game_id}: {message}")
                
                # Send back game state info instead of echo
                game_service = get_game_service()
                game = await game_service.get_game_state(game_id)
                if game:
                    # Pull rules from settings
                    try:
                        from app.config import settings
                        turn_seconds = int(getattr(settings, "TURN_SECONDS", 30))
                    except Exception:
                        turn_seconds = 30
                    
                    response = {
                        "type": "game_status",
                        "current_player_id": game.current_player_id,
                        "current_player_name": game.player1_name if game.current_player_id == game.player1_id else game.player2_name,
                        "round": game.round,
                        "player1": {
                            "name": game.player1_name,
                            "score": game.player1_score,
                            "moves_left": game.player1_moves_left,
                            "bombs": game.player1_bombs
                        },
                        "player2": {
                            "name": game.player2_name,
                            "score": game.player2_score,
                            "moves_left": game.player2_moves_left,
                            "bombs": game.player2_bombs
                        },
                        "turn_deadline": game.current_turn_deadline.isoformat() if game.current_turn_deadline else None,
                        "turn_seconds": turn_seconds
                    }
                    await websocket.send_text(json.dumps(response))
                else:
                    await websocket.send_text(json.dumps({"type": "error", "message": "Game not found"}))
                    
            except json.JSONDecodeError:
                # If not valid JSON, send simple acknowledgment
                await websocket.send_text(json.dumps({"type": "ack", "message": "Message received"}))
            except Exception as e:
                logger.error(f"[WS] Error processing message in game {game_id}: {e}")
                await websocket.send_text(json.dumps({"type": "error", "message": "Failed to process message"}))
                
    except WebSocketDisconnect:
        manager.disconnect(game_id)
