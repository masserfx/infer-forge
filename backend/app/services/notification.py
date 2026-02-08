"""Notification service for CRUD operations and WebSocket broadcasting."""

from uuid import UUID

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.websocket import manager
from app.models.notification import Notification, NotificationType

logger = structlog.get_logger(__name__)


class NotificationService:
    """Service for managing notifications with WebSocket broadcast."""

    def __init__(self, db: AsyncSession):
        """Initialize service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def create(
        self,
        user_id: UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        link: str | None = None,
    ) -> Notification:
        """Create a notification and broadcast via WebSocket.

        Args:
            user_id: Target user UUID.
            notification_type: Notification type enum.
            title: Notification title (Czech).
            message: Notification body text.
            link: Optional link to related resource.

        Returns:
            Created notification instance.
        """
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            link=link,
        )
        self.db.add(notification)
        await self.db.flush()
        await self.db.refresh(notification)

        # Broadcast via WebSocket/Redis
        ws_message = {
            "type": notification_type.value,
            "title": title,
            "message": message,
            "link": link,
            "notification_id": str(notification.id),
        }
        await manager.publish_notification(str(user_id), ws_message)

        await logger.ainfo(
            "notification_created",
            user_id=str(user_id),
            type=notification_type.value,
            notification_id=str(notification.id),
        )
        return notification

    async def create_for_all(
        self,
        notification_type: NotificationType,
        title: str,
        message: str,
        link: str | None = None,
        user_ids: list[UUID] | None = None,
    ) -> list[Notification]:
        """Create notifications for multiple users.

        Args:
            notification_type: Notification type.
            title: Title text.
            message: Body text.
            link: Optional link.
            user_ids: Specific user IDs. If None, broadcasts to all connected users.

        Returns:
            List of created notifications.
        """
        notifications = []
        if user_ids:
            for uid in user_ids:
                n = await self.create(uid, notification_type, title, message, link)
                notifications.append(n)
        else:
            # Broadcast to all connected without persisting per-user
            ws_message = {
                "type": notification_type.value,
                "title": title,
                "message": message,
                "link": link,
            }
            await manager.broadcast(ws_message)

        return notifications

    async def get_user_notifications(
        self,
        user_id: UUID,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        """Get notifications for a user.

        Args:
            user_id: User UUID.
            unread_only: If True, return only unread notifications.
            skip: Pagination offset.
            limit: Max results.

        Returns:
            List of notifications.
        """
        query = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            query = query.where(Notification.read.is_(False))

        query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_unread_count(self, user_id: UUID) -> int:
        """Get count of unread notifications.

        Args:
            user_id: User UUID.

        Returns:
            Count of unread notifications.
        """
        result = await self.db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.read.is_(False),
            )
        )
        return result.scalar() or 0

    async def mark_read(self, notification_id: UUID, user_id: UUID) -> Notification | None:
        """Mark single notification as read.

        Args:
            notification_id: Notification UUID.
            user_id: User UUID (ownership check).

        Returns:
            Updated notification or None if not found.
        """
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        notification = result.scalar_one_or_none()
        if notification:
            notification.read = True
            await self.db.flush()
            await self.db.refresh(notification)
        return notification

    async def mark_all_read(self, user_id: UUID) -> int:
        """Mark all user's notifications as read.

        Args:
            user_id: User UUID.

        Returns:
            Number of notifications updated.
        """
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read.is_(False),
            )
            .values(read=True)
        )
        await self.db.flush()
        return result.rowcount or 0
