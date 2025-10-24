"""WebSocket connection management module."""

from typing import Dict, List
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time game updates.

    Attributes:
        active_connections: Dictionary mapping game IDs to lists of active WebSocket connections
    """
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, game_id: str):
        """Accept a new WebSocket connection and add it to the active connections."""
        await websocket.accept()
        self.active_connections.setdefault(game_id, []).append(websocket)
        connections = len(self.active_connections[game_id])
        logger.info(f"[WS] Player connected to game {game_id}. Total connections: {connections}")

    def disconnect(self, game_id: str):
        """Remove disconnected sockets for a game and clean up if no active connections remain."""
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
        """Send a message to all players connected to a specific game.

        Args:
            message: Dictionary containing the message data
            game_id: ID of the game to send the message to
        """
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


# Singleton instance to be used by routes
manager = ConnectionManager()
