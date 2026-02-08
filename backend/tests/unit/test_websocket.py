"""Unit tests for WebSocket ConnectionManager."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocket

from app.core.websocket import ConnectionManager


class TestConnectionManager:
    """Tests for WebSocket ConnectionManager."""

    @pytest.fixture
    def manager(self) -> ConnectionManager:
        """Create a fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self) -> AsyncMock:
        """Create mock WebSocket."""
        mock = AsyncMock(spec=WebSocket)
        mock.accept = AsyncMock()
        mock.send_json = AsyncMock()
        mock.close = AsyncMock()
        return mock

    @pytest.fixture
    def mock_redis(self) -> AsyncMock:
        """Create mock Redis client."""
        mock = AsyncMock()
        mock.publish = AsyncMock()
        mock.close = AsyncMock()

        # Mock pubsub
        pubsub_mock = AsyncMock()
        pubsub_mock.subscribe = AsyncMock()
        pubsub_mock.unsubscribe = AsyncMock()
        pubsub_mock.close = AsyncMock()

        async def listen_generator():
            """Mock async generator for pubsub.listen()."""
            # Return empty to prevent infinite loop in tests
            return
            yield  # Make it a generator

        pubsub_mock.listen = listen_generator
        mock.pubsub.return_value = pubsub_mock

        return mock

    async def test_initialize_redis(self, manager: ConnectionManager) -> None:
        """Test initializing Redis connection."""
        with patch("app.core.websocket.Redis") as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis_class.from_url.return_value = mock_redis

            with patch("app.core.websocket.settings") as mock_settings:
                mock_settings.REDIS_URL = "redis://localhost:6379"
                await manager.initialize()

            mock_redis_class.from_url.assert_called_once()
            assert manager._redis is not None
            assert manager._pubsub_task is not None
            assert manager._initialized is True

    async def test_connect_websocket(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        """Test connecting a WebSocket."""
        user_id = "test-user-123"

        await manager.connect(mock_websocket, user_id)

        mock_websocket.accept.assert_awaited_once()
        assert user_id in manager.active_connections
        assert mock_websocket in manager.active_connections[user_id]

    async def test_connect_multiple_websockets_same_user(
        self, manager: ConnectionManager
    ) -> None:
        """Test connecting multiple WebSockets for same user."""
        user_id = "test-user-123"
        ws1 = AsyncMock(spec=WebSocket)
        ws1.accept = AsyncMock()
        ws2 = AsyncMock(spec=WebSocket)
        ws2.accept = AsyncMock()

        await manager.connect(ws1, user_id)
        await manager.connect(ws2, user_id)

        assert len(manager.active_connections[user_id]) == 2
        assert ws1 in manager.active_connections[user_id]
        assert ws2 in manager.active_connections[user_id]

    async def test_disconnect_websocket(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        """Test disconnecting a WebSocket."""
        user_id = "test-user-123"
        manager.active_connections[user_id] = [mock_websocket]

        await manager.disconnect(mock_websocket, user_id)

        assert user_id not in manager.active_connections

    async def test_disconnect_one_of_multiple(self, manager: ConnectionManager) -> None:
        """Test disconnecting one WebSocket when user has multiple."""
        user_id = "test-user-123"
        ws1 = MagicMock(spec=WebSocket)
        ws2 = MagicMock(spec=WebSocket)
        manager.active_connections[user_id] = [ws1, ws2]

        await manager.disconnect(ws1, user_id)

        assert user_id in manager.active_connections
        assert len(manager.active_connections[user_id]) == 1
        assert ws2 in manager.active_connections[user_id]

    async def test_disconnect_nonexistent_user(self, manager: ConnectionManager) -> None:
        """Test disconnecting for non-existent user (should not raise)."""
        user_id = "nonexistent"
        mock_ws = MagicMock(spec=WebSocket)

        # Should not raise
        await manager.disconnect(mock_ws, user_id)

    async def test_send_to_user(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        """Test sending message to a specific user."""
        user_id = "test-user-123"
        manager.active_connections[user_id] = [mock_websocket]
        message = {"type": "test", "data": "hello"}

        await manager.send_to_user(user_id, message)

        mock_websocket.send_json.assert_awaited_once_with(message)

    async def test_send_to_user_multiple_connections(
        self, manager: ConnectionManager
    ) -> None:
        """Test sending to user with multiple connections."""
        user_id = "test-user-123"
        ws1 = AsyncMock(spec=WebSocket)
        ws1.send_json = AsyncMock()
        ws2 = AsyncMock(spec=WebSocket)
        ws2.send_json = AsyncMock()

        manager.active_connections[user_id] = [ws1, ws2]
        message = {"type": "test", "data": "hello"}

        await manager.send_to_user(user_id, message)

        ws1.send_json.assert_awaited_once_with(message)
        ws2.send_json.assert_awaited_once_with(message)

    async def test_send_to_user_not_connected(
        self, manager: ConnectionManager
    ) -> None:
        """Test sending to non-connected user (should not raise)."""
        message = {"type": "test", "data": "hello"}

        # Should not raise
        await manager.send_to_user("nonexistent-user", message)

    async def test_send_to_user_handles_disconnected_client(
        self, manager: ConnectionManager
    ) -> None:
        """Test that disconnected clients are cleaned up on send failure."""
        user_id = "test-user-123"
        ws_working = AsyncMock(spec=WebSocket)
        ws_working.send_json = AsyncMock()

        ws_broken = AsyncMock(spec=WebSocket)
        ws_broken.send_json = AsyncMock(side_effect=RuntimeError("Connection closed"))

        manager.active_connections[user_id] = [ws_working, ws_broken]
        message = {"type": "test", "data": "hello"}

        await manager.send_to_user(user_id, message)

        # Working connection should receive message
        ws_working.send_json.assert_awaited_once()

        # Broken connection should be removed
        assert ws_broken not in manager.active_connections[user_id]
        assert ws_working in manager.active_connections[user_id]

    async def test_broadcast(self, manager: ConnectionManager) -> None:
        """Test broadcasting to all connected users."""
        user1 = "user-1"
        user2 = "user-2"
        ws1 = AsyncMock(spec=WebSocket)
        ws1.send_json = AsyncMock()
        ws2 = AsyncMock(spec=WebSocket)
        ws2.send_json = AsyncMock()

        manager.active_connections[user1] = [ws1]
        manager.active_connections[user2] = [ws2]

        message = {"type": "broadcast", "data": "hello all"}
        await manager.broadcast(message)

        ws1.send_json.assert_awaited_once_with(message)
        ws2.send_json.assert_awaited_once_with(message)

    async def test_broadcast_all_users(self, manager: ConnectionManager) -> None:
        """Test broadcasting to all users (no exclude parameter)."""
        user1 = "user-1"
        user2 = "user-2"
        ws1 = AsyncMock(spec=WebSocket)
        ws1.send_json = AsyncMock()
        ws2 = AsyncMock(spec=WebSocket)
        ws2.send_json = AsyncMock()

        manager.active_connections[user1] = [ws1]
        manager.active_connections[user2] = [ws2]

        message = {"type": "broadcast", "data": "hello"}
        await manager.broadcast(message)

        ws1.send_json.assert_awaited_once_with(message)
        ws2.send_json.assert_awaited_once_with(message)

    async def test_publish_notification_to_redis(self, manager: ConnectionManager) -> None:
        """Test publishing message to Redis."""
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock()
        manager._redis = mock_redis

        user_id = "test-user-123"
        message = {"type": "test", "title": "Test"}

        await manager.publish_notification(user_id, message)

        mock_redis.publish.assert_awaited_once()
        call_args = mock_redis.publish.call_args
        assert call_args[0][0] == "notifications"

        published_data = json.loads(call_args[0][1])
        assert published_data["user_id"] == user_id
        assert published_data["message"] == message

    async def test_publish_notification_without_redis(self, manager: ConnectionManager) -> None:
        """Test publish when Redis is not initialized (should not raise)."""
        manager._redis = None
        message = {"type": "test"}

        # Should not raise
        await manager.publish_notification("user-123", message)

    async def test_close_manager(self, manager: ConnectionManager) -> None:
        """Test closing manager and cleanup."""
        # Setup connections
        ws1 = AsyncMock(spec=WebSocket)
        ws1.close = AsyncMock()
        ws2 = AsyncMock(spec=WebSocket)
        ws2.close = AsyncMock()

        manager.active_connections["user-1"] = [ws1]
        manager.active_connections["user-2"] = [ws2]

        # Setup Redis
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        manager._redis = mock_redis
        manager._initialized = True

        # Setup pubsub task
        manager._pubsub_task = asyncio.create_task(asyncio.sleep(10))

        await manager.close()

        # Verify cleanup
        assert len(manager.active_connections) == 0
        ws1.close.assert_awaited_once()
        ws2.close.assert_awaited_once()
        mock_redis.close.assert_awaited_once()
        assert manager._redis is None
        assert manager._initialized is False

    async def test_close_handles_websocket_errors(
        self, manager: ConnectionManager
    ) -> None:
        """Test that close handles WebSocket close errors gracefully."""
        ws = AsyncMock(spec=WebSocket)
        ws.close = AsyncMock(side_effect=Exception("Already closed"))

        manager.active_connections["user-1"] = [ws]

        # Should not raise
        await manager.close()

        assert len(manager.active_connections) == 0
