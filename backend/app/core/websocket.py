"""WebSocket connection manager with Redis pub/sub for multi-worker broadcast."""

import asyncio
import json
from typing import Any

import structlog
from fastapi import WebSocket
from redis.asyncio import Redis
from starlette.websockets import WebSocketDisconnect

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

CHANNEL_NAME = "notifications"


class ConnectionManager:
    """Manages WebSocket connections and Redis pub/sub broadcasting."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        self.active_connections: dict[str, list[WebSocket]] = {}
        self._redis: Redis | None = None
        self._pubsub_task: asyncio.Task[None] | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Redis connection and start pub/sub listener."""
        if self._initialized:
            return

        redis_url = str(settings.REDIS_URL)
        self._redis = Redis.from_url(redis_url, decode_responses=False)
        self._pubsub_task = asyncio.create_task(self.start_redis_listener())
        self._initialized = True
        await logger.ainfo("websocket_manager_initialized", redis_url=redis_url)

    async def close(self) -> None:
        """Close all connections and cleanup Redis."""
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass

        # Close all WebSocket connections
        for _user_id, connections in self.active_connections.items():
            for ws in connections:
                try:
                    await ws.close()
                except Exception:
                    await logger.awarning("websocket_close_failed", user_id=_user_id)
        self.active_connections.clear()

        if self._redis:
            await self._redis.close()
            self._redis = None

        self._initialized = False
        await logger.ainfo("websocket_manager_closed")

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """Register a new WebSocket connection for a user.

        Args:
            websocket: WebSocket connection.
            user_id: User UUID string.
        """
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        await logger.ainfo(
            "websocket_connected",
            user_id=user_id,
            total_users=len(self.active_connections),
        )

    async def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """Remove a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove.
            user_id: User UUID string.
        """
        if user_id in self.active_connections:
            self.active_connections[user_id] = [
                ws for ws in self.active_connections[user_id] if ws is not websocket
            ]
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        await logger.ainfo("websocket_disconnected", user_id=user_id)

    async def send_to_user(self, user_id: str, message: dict[str, Any]) -> None:
        """Send message to all connections of a specific user.

        Args:
            user_id: Target user UUID string.
            message: JSON-serializable message dict.
        """
        if user_id in self.active_connections:
            dead_connections: list[WebSocket] = []
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_json(message)
                except (WebSocketDisconnect, RuntimeError):
                    dead_connections.append(ws)

            # Clean up dead connections
            for ws in dead_connections:
                await self.disconnect(ws, user_id)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast message to all connected users.

        Args:
            message: JSON-serializable message dict.
        """
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(user_id, message)

    async def publish_notification(self, user_id: str, data: dict[str, Any]) -> None:
        """Publish notification via Redis for multi-worker broadcast.

        Args:
            user_id: Target user UUID string.
            data: Notification data.
        """
        if self._redis:
            payload = json.dumps({"user_id": user_id, "message": data})
            await self._redis.publish(CHANNEL_NAME, payload)

    async def start_redis_listener(self) -> None:
        """Listen for notifications from Redis pub/sub and forward to WebSocket."""
        if not self._redis:
            return

        pubsub = self._redis.pubsub()
        await pubsub.subscribe(CHANNEL_NAME)
        await logger.ainfo("redis_listener_started", channel=CHANNEL_NAME)

        try:
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    try:
                        data = json.loads(msg["data"])
                        user_id = data.get("user_id")
                        message = data.get("message", {})

                        if user_id:
                            await self.send_to_user(user_id, message)
                        else:
                            await self.broadcast(message)
                    except (json.JSONDecodeError, KeyError) as e:
                        await logger.awarning(
                            "invalid_redis_message",
                            error=str(e),
                        )
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(CHANNEL_NAME)
            await pubsub.close()


# Global singleton
manager = ConnectionManager()
