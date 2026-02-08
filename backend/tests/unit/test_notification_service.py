"""Unit tests for NotificationService."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType
from app.services.notification import NotificationService


class TestNotificationService:
    """Tests for NotificationService."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        mock = AsyncMock(spec=AsyncSession)
        mock.add = MagicMock()
        mock.flush = AsyncMock()
        mock.refresh = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def mock_manager(self) -> AsyncMock:
        """Create mock WebSocket manager."""
        with patch("app.services.notification.manager") as mock:
            mock.publish_notification = AsyncMock()
            mock.broadcast = AsyncMock()
            yield mock

    async def test_create_notification(
        self, mock_db: AsyncMock, mock_manager: AsyncMock
    ) -> None:
        """Test creating a notification and broadcasting via WebSocket."""
        service = NotificationService(mock_db)
        user_id = uuid.uuid4()

        await service.create(
            user_id=user_id,
            notification_type=NotificationType.EMAIL_NEW,
            title="Nový email",
            message="Máte nový email od zákazníka",
            link="/inbox/123",
        )

        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

        # Verify notification attributes
        added_notification = mock_db.add.call_args[0][0]
        assert isinstance(added_notification, Notification)
        assert added_notification.user_id == user_id
        assert added_notification.type == NotificationType.EMAIL_NEW
        assert added_notification.title == "Nový email"
        assert added_notification.message == "Máte nový email od zákazníka"
        assert added_notification.link == "/inbox/123"

        # Verify WebSocket broadcast
        mock_manager.publish_notification.assert_awaited_once()
        publish_call = mock_manager.publish_notification.call_args
        assert publish_call[0][0] == str(user_id)
        ws_message = publish_call[0][1]
        assert ws_message["type"] == "email_new"
        assert ws_message["title"] == "Nový email"
        assert ws_message["message"] == "Máte nový email od zákazníka"
        assert ws_message["link"] == "/inbox/123"
        assert "notification_id" in ws_message

    async def test_create_notification_without_link(
        self, mock_db: AsyncMock, mock_manager: AsyncMock
    ) -> None:
        """Test creating notification without optional link."""
        service = NotificationService(mock_db)
        user_id = uuid.uuid4()

        await service.create(
            user_id=user_id,
            notification_type=NotificationType.CALCULATION_COMPLETE,
            title="Kalkulace hotova",
            message="Kalkulace byla dokončena",
        )

        added_notification = mock_db.add.call_args[0][0]
        assert added_notification.link is None

        # Verify WebSocket message
        ws_message = mock_manager.publish_notification.call_args[0][1]
        assert ws_message["link"] is None

    async def test_create_for_all_with_user_ids(
        self, mock_db: AsyncMock, mock_manager: AsyncMock
    ) -> None:
        """Test creating notifications for specific users."""
        service = NotificationService(mock_db)
        user_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]

        notifications = await service.create_for_all(
            notification_type=NotificationType.POHODA_SYNC_COMPLETE,
            title="Pohoda synchronizace",
            message="Synchronizace s Pohoda dokončena",
            user_ids=user_ids,
        )

        # Should create notification for each user
        assert len(notifications) == 3
        assert mock_db.add.call_count == 3
        assert mock_manager.publish_notification.await_count == 3

    async def test_create_for_all_broadcast(
        self, mock_db: AsyncMock, mock_manager: AsyncMock
    ) -> None:
        """Test broadcasting notification to all connected users."""
        service = NotificationService(mock_db)

        notifications = await service.create_for_all(
            notification_type=NotificationType.ORDER_STATUS_CHANGED,
            title="Systémová zpráva",
            message="Probíhá údržba systému",
        )

        # Should broadcast without persisting
        assert len(notifications) == 0
        mock_db.add.assert_not_called()
        mock_manager.broadcast.assert_awaited_once()

        broadcast_message = mock_manager.broadcast.call_args[0][0]
        assert broadcast_message["type"] == "order_status_changed"
        assert broadcast_message["title"] == "Systémová zpráva"
        assert broadcast_message["message"] == "Probíhá údržba systému"

    async def test_get_user_notifications_all(self, mock_db: AsyncMock) -> None:
        """Test retrieving all notifications for a user."""
        service = NotificationService(mock_db)
        user_id = uuid.uuid4()

        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            Notification(
                id=uuid.uuid4(),
                user_id=user_id,
                type=NotificationType.EMAIL_NEW,
                title="Test 1",
                message="Message 1",
                read=False,
            ),
            Notification(
                id=uuid.uuid4(),
                user_id=user_id,
                type=NotificationType.CALCULATION_COMPLETE,
                title="Test 2",
                message="Message 2",
                read=True,
            ),
        ]
        mock_db.execute.return_value = mock_result

        notifications = await service.get_user_notifications(user_id)

        assert len(notifications) == 2
        mock_db.execute.assert_awaited_once()

    async def test_get_user_notifications_unread_only(self, mock_db: AsyncMock) -> None:
        """Test retrieving only unread notifications."""
        service = NotificationService(mock_db)
        user_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            Notification(
                id=uuid.uuid4(),
                user_id=user_id,
                type=NotificationType.EMAIL_NEW,
                title="Unread",
                message="Unread message",
                read=False,
            ),
        ]
        mock_db.execute.return_value = mock_result

        notifications = await service.get_user_notifications(
            user_id, unread_only=True
        )

        assert len(notifications) == 1
        assert notifications[0].read is False
        mock_db.execute.assert_awaited_once()

    async def test_get_user_notifications_pagination(self, mock_db: AsyncMock) -> None:
        """Test notification pagination."""
        service = NotificationService(mock_db)
        user_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await service.get_user_notifications(user_id, skip=10, limit=20)

        mock_db.execute.assert_awaited_once()
        # Query should include offset and limit

    async def test_get_unread_count(self, mock_db: AsyncMock) -> None:
        """Test getting count of unread notifications."""
        service = NotificationService(mock_db)
        user_id = uuid.uuid4()

        # Mock count result
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_db.execute.return_value = mock_result

        count = await service.get_unread_count(user_id)

        assert count == 5
        mock_db.execute.assert_awaited_once()

    async def test_get_unread_count_zero(self, mock_db: AsyncMock) -> None:
        """Test getting count when no unread notifications."""
        service = NotificationService(mock_db)
        user_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_db.execute.return_value = mock_result

        count = await service.get_unread_count(user_id)

        assert count == 0

    async def test_mark_read(self, mock_db: AsyncMock) -> None:
        """Test marking single notification as read."""
        service = NotificationService(mock_db)
        user_id = uuid.uuid4()
        notification_id = uuid.uuid4()

        # Mock notification found
        mock_notification = Notification(
            id=notification_id,
            user_id=user_id,
            type=NotificationType.EMAIL_NEW,
            title="Test",
            message="Test message",
            read=False,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_notification
        mock_db.execute.return_value = mock_result

        result = await service.mark_read(notification_id, user_id)

        assert result is not None
        assert result.read is True
        mock_db.execute.assert_awaited_once()
        mock_db.flush.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    async def test_mark_read_not_found(self, mock_db: AsyncMock) -> None:
        """Test marking notification that doesn't belong to user."""
        service = NotificationService(mock_db)
        user_id = uuid.uuid4()
        notification_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.mark_read(notification_id, user_id)

        assert result is None

    async def test_mark_all_read(self, mock_db: AsyncMock) -> None:
        """Test marking all user notifications as read."""
        service = NotificationService(mock_db)
        user_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.rowcount = 10
        mock_db.execute.return_value = mock_result

        count = await service.mark_all_read(user_id)

        assert count == 10
        mock_db.execute.assert_awaited_once()
        mock_db.flush.assert_awaited_once()

    async def test_mark_all_read_none_unread(self, mock_db: AsyncMock) -> None:
        """Test marking all as read when no unread notifications."""
        service = NotificationService(mock_db)
        user_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result

        count = await service.mark_all_read(user_id)

        assert count == 0
