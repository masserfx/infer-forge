"""WebSocket endpoint for real-time notifications."""

import asyncio
import json
from uuid import UUID

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.database import AsyncSessionLocal
from app.core.security import verify_token
from app.core.websocket import manager
from app.services.auth import AuthService

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["WebSocket"])

# Timeout for authentication message after connection
_AUTH_TIMEOUT_SECONDS = 10.0


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time notifications.

    Authentication: send {"type": "auth", "token": "JWT"} as first message
    after connection. Token must arrive within 10 seconds.

    Supports:
    - Receiving notifications as JSON messages
    - Ping/pong keepalive (30s interval from client)
    """
    await websocket.accept()

    # Wait for auth message (token in first message, not URL)
    try:
        raw = await asyncio.wait_for(
            websocket.receive_text(), timeout=_AUTH_TIMEOUT_SECONDS
        )
        auth_msg = json.loads(raw)
        token = auth_msg.get("token", "") if isinstance(auth_msg, dict) else ""
    except (asyncio.TimeoutError, json.JSONDecodeError, WebSocketDisconnect):
        await websocket.close(code=4001, reason="Authentication timeout")
        return

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

    await websocket.send_text(json.dumps({"type": "auth_ok"}))

    await manager.connect(websocket, user_id_str)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id_str)
    except Exception as e:
        logger.warning("websocket_error", user_id=user_id_str, error=str(e))
        await manager.disconnect(websocket, user_id_str)
