"""WebSocket endpoint for real-time notifications."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.database import AsyncSessionLocal
from app.core.security import verify_token
from app.core.websocket import manager
from app.services.auth import AuthService

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT auth token"),
) -> None:
    """WebSocket endpoint for real-time notifications.

    Authentication via query param: /ws?token=JWT

    Supports:
    - Receiving notifications as JSON messages
    - Ping/pong keepalive (30s interval from client)
    """
    # Authenticate via JWT token
    payload = verify_token(token)
    if not payload or not payload.get("sub"):
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id_str = payload["sub"]

    # Verify user exists and is active
    async with AsyncSessionLocal() as db:
        auth_service = AuthService(db)
        user = await auth_service.get_by_id(UUID(user_id_str))
        if user is None or not user.is_active:
            await websocket.close(code=4003, reason="User not found or inactive")
            return

    await manager.connect(websocket, user_id_str)
    try:
        while True:
            # Wait for messages (ping/pong or commands)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id_str)
    except Exception as e:
        await logger.awarning("websocket_error", user_id=user_id_str, error=str(e))
        await manager.disconnect(websocket, user_id_str)
