from __future__ import annotations

import asyncio
import uuid
from typing import Dict, List, Tuple, Optional
from time import monotonic

from fastapi import WebSocket
from app.services.game_service import GameService


class MatchmakingManager:
    """In-memory matchmaking that pairs players and notifies them via WebSockets.

    Notes:
    - Uses a simple FIFO queue and requires both players to have active sockets.
    - On match, a `GameSession` is created via `GameService` and both players get
      a `match_found` message containing the `game_session_id` and `your_turn`.
    """

    def __init__(self) -> None:
        # (uniq_id, name, joined_at_monotonic)
        self._queue: List[Tuple[str, str, float]] = []
        self._connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()
        self._game_service = GameService()
        self._queue_entry_ttl_seconds: float = 300.0

    async def register_connection(self, uniq_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections[uniq_id] = websocket

    async def unregister_connection(self, uniq_id: str) -> None:
        async with self._lock:
            self._connections.pop(uniq_id, None)
            # Best-effort remove from queue as well
            self._queue = [e for e in self._queue if e[0] != uniq_id]

    async def join_queue(self, uniq_id: str, name: str) -> None:
        async with self._lock:
            # Avoid duplicates in queue
            if not any(u == uniq_id for u, _, __ in self._queue):
                self._queue.append((uniq_id, name, monotonic()))

    def _prune_queue_locked(self) -> None:
        """Remove stale queue entries (no socket or timed out). Must be called with lock held."""
        now = monotonic()
        fresh: List[Tuple[str, str, float]] = []
        for uniq_id, name, joined_at in self._queue:
            if uniq_id not in self._connections:
                # Drop entries without an active socket
                continue
            if now - joined_at > self._queue_entry_ttl_seconds:
                # Drop entries waiting too long
                continue
            fresh.append((uniq_id, name, joined_at))
        self._queue = fresh

    async def try_match(self) -> Optional[Tuple[str, str, str]]:
        """Match two queued players with active sockets.

        Returns (game_session_id, p1_uniq_id, p2_uniq_id) if matched, else None.
        """
        async with self._lock:
            # Need at least two players in queue
            self._prune_queue_locked()
            if len(self._queue) < 2:
                return None

            # Find first pair that both have sockets connected
            for i in range(len(self._queue)):
                for j in range(i + 1, len(self._queue)):
                    p1_id, p1_name, _ = self._queue[i]
                    p2_id, p2_name, __ = self._queue[j]

                    if p1_id in self._connections and p2_id in self._connections:
                        # Remove them from queue by indices (higher index first)
                        self._queue.pop(j)
                        self._queue.pop(i)

                        # Create actual game session in database
                        try:
                            game_session = await self._game_service.create_game_session(
                                p1_id, p1_name, p2_id, p2_name
                            )
                            game_session_id = game_session.id or str(game_session._id)
                        except Exception as e:
                            # If game creation fails, put players back in queue
                            self._queue.append((p1_id, p1_name))
                            self._queue.append((p2_id, p2_name))
                            return None

                        # Send notifications outside the lock to avoid blocking others
                        asyncio.create_task(
                            self._notify_match(
                                game_session_id,
                                p1_id,
                                p1_name,
                                p2_id,
                                p2_name,
                                your_turn=True,  # Player 1 starts
                            )
                        )
                        asyncio.create_task(
                            self._notify_match(
                                game_session_id,
                                p2_id,
                                p2_name,
                                p1_id,
                                p1_name,
                                your_turn=False,  # Player 2 waits
                            )
                        )

                        return game_session_id, p1_id, p2_id

            return None

    async def _notify_match(
        self,
        game_session_id: str,
        uniq_id: str,
        player_name: str,
        opponent_id: str,
        opponent_name: str,
        *,
        your_turn: bool = False,
    ) -> None:
        message = {
            "type": "match_found",
            "game_session_id": game_session_id,
            "opponent_name": opponent_name,
            "your_turn": your_turn,
        }
        websocket = self._connections.get(uniq_id)
        if websocket is not None:
            try:
                await websocket.send_json(message)
            except Exception:
                # Best-effort; if sending fails, drop connection
                await self.unregister_connection(uniq_id)


# Singleton instance to be used by routes
matchmaking_manager = MatchmakingManager()
