from __future__ import annotations

import asyncio
import uuid
from typing import Dict, List, Tuple, Optional

from fastapi import WebSocket


class MatchmakingManager:
    """In-memory matchmaking manager that pairs players and notifies them via websockets."""

    def __init__(self) -> None:
        self._queue: List[Tuple[str, str]] = []  # (uniq_id, name)
        self._connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def register_connection(self, uniq_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections[uniq_id] = websocket

    async def unregister_connection(self, uniq_id: str) -> None:
        async with self._lock:
            self._connections.pop(uniq_id, None)

    async def join_queue(self, uniq_id: str, name: str) -> None:
        async with self._lock:
            # Avoid duplicates in queue
            if not any(u == uniq_id for u, _ in self._queue):
                self._queue.append((uniq_id, name))

    async def try_match(self) -> Optional[Tuple[str, str, str]]:
        """Try to match two queued players that both have active websocket connections.

        Returns a tuple (game_session_id, p1_uniq_id, p2_uniq_id) if matched, else None.
        """
        async with self._lock:
            # Need at least two players in queue
            if len(self._queue) < 2:
                return None

            # Find first pair that both have sockets connected
            for i in range(len(self._queue)):
                for j in range(i + 1, len(self._queue)):
                    p1_id, p1_name = self._queue[i]
                    p2_id, p2_name = self._queue[j]

                    if p1_id in self._connections and p2_id in self._connections:
                        # Remove them from queue by indices (higher index first)
                        self._queue.pop(j)
                        self._queue.pop(i)

                        game_session_id = str(uuid.uuid4())

                        # Send notifications outside the lock to avoid blocking others
                        asyncio.create_task(
                            self._notify_match(
                                game_session_id,
                                p1_id,
                                p1_name,
                                p2_id,
                                p2_name,
                            )
                        )
                        asyncio.create_task(
                            self._notify_match(
                                game_session_id,
                                p2_id,
                                p2_name,
                                p1_id,
                                p1_name,
                                your_turn=True,
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
