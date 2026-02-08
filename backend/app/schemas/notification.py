"""Pydantic schemas for notifications."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.notification import NotificationType


class NotificationCreate(BaseModel):
    """Schema for creating a notification."""

    type: NotificationType
    title: str
    message: str
    link: str | None = None


class NotificationResponse(BaseModel):
    """Notification response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    type: NotificationType
    title: str
    message: str
    link: str | None
    read: bool
    created_at: datetime


class NotificationList(BaseModel):
    """List of notifications with unread count."""

    items: list[NotificationResponse]
    unread_count: int
