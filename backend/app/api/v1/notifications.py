"""Notification REST API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.notification import NotificationList, NotificationResponse
from app.services.notification import NotificationService

router = APIRouter(prefix="/notifikace", tags=["Notifikace"])


@router.get("", response_model=NotificationList)
async def get_notifications(
    unread_only: bool = Query(default=False, description="Only unread notifications"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationList:
    """Get current user's notifications."""
    service = NotificationService(db)
    notifications = await service.get_user_notifications(
        user_id=user.id,
        unread_only=unread_only,
        skip=skip,
        limit=limit,
    )
    unread_count = await service.get_unread_count(user.id)

    return NotificationList(
        items=[NotificationResponse.model_validate(n) for n in notifications],
        unread_count=unread_count,
    )


@router.get("/count", response_model=dict[str, int])
async def get_unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Get count of unread notifications."""
    service = NotificationService(db)
    count = await service.get_unread_count(user.id)
    return {"unread_count": count}


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    """Mark single notification as read."""
    service = NotificationService(db)
    notification = await service.mark_read(notification_id, user.id)
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notifikace nenalezena",
        )
    await db.commit()
    return NotificationResponse.model_validate(notification)


@router.patch("/read-all", response_model=dict[str, int])
async def mark_all_notifications_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Mark all notifications as read."""
    service = NotificationService(db)
    count = await service.mark_all_read(user.id)
    await db.commit()
    return {"marked_read": count}
