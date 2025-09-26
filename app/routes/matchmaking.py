from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel

from app.database.user_repository import UserRepository
from app.services.matchmaking import matchmaking_manager


router = APIRouter(prefix="/matchmaking", tags=["matchmaking"])


def get_user_repo():
    return UserRepository()


class JoinQueueRequest(BaseModel):
    """HTTP payload to join matchmaking queue.

    Unity sends uniqId + name over HTTP as a backup to the WS init message.
    """
    uniqId: str
    name: str


@router.post("/join")
async def join_matchmaking_queue(payload: JoinQueueRequest, user_repo: UserRepository = Depends(get_user_repo)):
    """Join the queue and attempt a match.

    This endpoint is idempotent and safe to call alongside the WebSocket
    initialization. It also best-effort creates a minimal user record.
    """
    # Ensure user exists (create on first join to simplify flow)
    user = await user_repo.find_by_unique_id(payload.uniqId)
    if not user:
        # Best-effort create minimal user
        from app.models.user import UserCreate
        user = await user_repo.create_user(UserCreate(uniqId=payload.uniqId))

    await matchmaking_manager.join_queue(payload.uniqId, payload.name)

    # Try to match immediately (best-effort)
    await matchmaking_manager.try_match()
    return {"status": "queued"}


@router.websocket("/ws")
async def matchmaking_ws(websocket: WebSocket):
    """WebSocket endpoint that registers the player and attempts to match.

    Expected first client message:
    {"uniqId": "abc123", "name": "PlayerName"}
    """
    await websocket.accept()
    uniq_id: str | None = None
    try:
        # Expect first message to be an auth/init message with uniqId and name
        init = await websocket.receive_json()
        uniq_id = init.get("uniqId")
        name = init.get("name")
        if not uniq_id or not name:
            await websocket.close(code=4400)
            return

        await matchmaking_manager.register_connection(uniq_id, websocket)
        
        # Join the matchmaking queue when connecting via WebSocket
        await matchmaking_manager.join_queue(uniq_id, name)

        # After connection, try to match in case a counterpart already queued
        await matchmaking_manager.try_match()

        # Keep the connection alive; ignore incoming messages for now
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        pass
    finally:
        if uniq_id:
            await matchmaking_manager.unregister_connection(uniq_id)
