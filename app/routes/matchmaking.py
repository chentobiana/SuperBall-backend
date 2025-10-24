from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.matchmaking import matchmaking_manager


router = APIRouter(prefix="/matchmaking", tags=["matchmaking"])


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
