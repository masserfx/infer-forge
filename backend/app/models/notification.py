"""Notification model for real-time alerts."""

import enum
from uuid import UUID

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPKMixin


class NotificationType(str, enum.Enum):
    """Types of notifications."""

    EMAIL_NEW = "email_new"
    EMAIL_CLASSIFIED = "email_classified"
    POHODA_SYNC_COMPLETE = "pohoda_sync_complete"
    CALCULATION_COMPLETE = "calculation_complete"
    ORDER_STATUS_CHANGED = "order_status_changed"
    DOCUMENT_UPLOADED = "document_uploaded"


class Notification(Base, UUIDPKMixin, TimestampMixin):
    """User notification for real-time alerts via WebSocket."""

    __tablename__ = "notifications"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, native_enum=False, length=50),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str | None] = mapped_column(String(512), nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_notifications_user_id", "user_id"),
        Index("ix_notifications_read", "read"),
    )

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, type={self.type.value}, read={self.read})>"
