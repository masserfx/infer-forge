"""Unit tests for Notification model."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType


class TestNotificationType:
    """Tests for NotificationType enum."""

    def test_notification_type_values(self) -> None:
        """Test all NotificationType enum values."""
        assert NotificationType.EMAIL_NEW.value == "email_new"
        assert NotificationType.EMAIL_CLASSIFIED.value == "email_classified"
        assert NotificationType.POHODA_SYNC_COMPLETE.value == "pohoda_sync_complete"
        assert NotificationType.CALCULATION_COMPLETE.value == "calculation_complete"
        assert NotificationType.ORDER_STATUS_CHANGED.value == "order_status_changed"
        assert NotificationType.DOCUMENT_UPLOADED.value == "document_uploaded"

    def test_notification_type_is_string_enum(self) -> None:
        """Test that NotificationType is a string enum."""
        assert isinstance(NotificationType.EMAIL_NEW.value, str)
        assert NotificationType.EMAIL_NEW == "email_new"


class TestNotificationModel:
    """Tests for Notification model."""

    async def test_create_notification(self, test_db: AsyncSession) -> None:
        """Test creating a notification record."""
        user_id = uuid.uuid4()

        notification = Notification(
            user_id=user_id,
            type=NotificationType.EMAIL_NEW,
            title="Nový email",
            message="Obdrželi jste nový email od zákazníka ABC s.r.o.",
            link="/inbox/123",
            read=False,
        )
        test_db.add(notification)
        await test_db.flush()

        assert notification.id is not None
        assert isinstance(notification.id, uuid.UUID)
        assert notification.user_id == user_id
        assert notification.type == NotificationType.EMAIL_NEW
        assert notification.title == "Nový email"
        assert notification.message == "Obdrželi jste nový email od zákazníka ABC s.r.o."
        assert notification.link == "/inbox/123"
        assert notification.read is False

    async def test_create_notification_without_link(
        self, test_db: AsyncSession
    ) -> None:
        """Test creating notification without optional link."""
        user_id = uuid.uuid4()

        notification = Notification(
            user_id=user_id,
            type=NotificationType.CALCULATION_COMPLETE,
            title="Kalkulace dokončena",
            message="Automatická kalkulace byla úspěšně dokončena",
        )
        test_db.add(notification)
        await test_db.flush()

        assert notification.id is not None
        assert notification.link is None
        assert notification.read is False  # Default value

    async def test_notification_timestamps(self, test_db: AsyncSession) -> None:
        """Test that timestamps are set automatically."""
        user_id = uuid.uuid4()

        notification = Notification(
            user_id=user_id,
            type=NotificationType.POHODA_SYNC_COMPLETE,
            title="Synchronizace dokončena",
            message="Data byla synchronizována s Pohoda",
        )
        test_db.add(notification)
        await test_db.flush()

        assert notification.created_at is not None
        assert notification.updated_at is not None

    async def test_notification_read_default(self, test_db: AsyncSession) -> None:
        """Test that read defaults to False."""
        user_id = uuid.uuid4()

        notification = Notification(
            user_id=user_id,
            type=NotificationType.ORDER_STATUS_CHANGED,
            title="Stav zakázky změněn",
            message="Zakázka ZAK-2024-001 přešla do výroby",
        )
        test_db.add(notification)
        await test_db.flush()

        assert notification.read is False

    async def test_notification_mark_as_read(self, test_db: AsyncSession) -> None:
        """Test marking notification as read."""
        user_id = uuid.uuid4()

        notification = Notification(
            user_id=user_id,
            type=NotificationType.DOCUMENT_UPLOADED,
            title="Dokument nahrán",
            message="Byl nahrán nový dokument",
            read=False,
        )
        test_db.add(notification)
        await test_db.flush()

        # Mark as read
        notification.read = True
        await test_db.flush()

        assert notification.read is True

    async def test_notification_repr(self, test_db: AsyncSession) -> None:
        """Test Notification string representation."""
        user_id = uuid.uuid4()

        notification = Notification(
            user_id=user_id,
            type=NotificationType.EMAIL_CLASSIFIED,
            title="Email klasifikován",
            message="Email byl automaticky klasifikován",
            read=False,
        )
        test_db.add(notification)
        await test_db.flush()

        repr_str = repr(notification)
        assert "Notification" in repr_str
        assert str(notification.id) in repr_str
        assert "email_classified" in repr_str
        assert "read=False" in repr_str

    async def test_notification_all_types(self, test_db: AsyncSession) -> None:
        """Test creating notifications with all notification types."""
        user_id = uuid.uuid4()

        for notification_type in NotificationType:
            notification = Notification(
                user_id=user_id,
                type=notification_type,
                title=f"Test {notification_type.value}",
                message=f"Testing {notification_type.value}",
            )
            test_db.add(notification)

        await test_db.flush()

        # No assertions needed, just verify all types work

    async def test_notification_long_message(self, test_db: AsyncSession) -> None:
        """Test notification with long message (Text field)."""
        user_id = uuid.uuid4()
        long_message = "A" * 5000  # Long text

        notification = Notification(
            user_id=user_id,
            type=NotificationType.EMAIL_NEW,
            title="Long message test",
            message=long_message,
        )
        test_db.add(notification)
        await test_db.flush()

        assert notification.message == long_message

    async def test_notification_max_title_length(self, test_db: AsyncSession) -> None:
        """Test notification title (String 255)."""
        user_id = uuid.uuid4()
        title = "T" * 255  # Max length

        notification = Notification(
            user_id=user_id,
            type=NotificationType.EMAIL_NEW,
            title=title,
            message="Test",
        )
        test_db.add(notification)
        await test_db.flush()

        assert notification.title == title

    async def test_notification_max_link_length(self, test_db: AsyncSession) -> None:
        """Test notification link (String 512)."""
        user_id = uuid.uuid4()
        link = "/inbox/" + "a" * 500  # Long link

        notification = Notification(
            user_id=user_id,
            type=NotificationType.EMAIL_NEW,
            title="Link test",
            message="Test",
            link=link,
        )
        test_db.add(notification)
        await test_db.flush()

        assert notification.link == link
