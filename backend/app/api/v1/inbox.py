"""Inbox API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models import InboxClassification, InboxStatus
from app.models.user import User, UserRole
from app.schemas import InboxAssign, InboxMessageResponse, InboxReclassify
from app.services import InboxService

router = APIRouter(prefix="/inbox", tags=["Inbox"])


@router.get("", response_model=list[InboxMessageResponse])
async def get_inbox_messages(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of records"),
    status: InboxStatus | None = Query(default=None, description="Filter by status"),
    classification: InboxClassification | None = Query(
        default=None, description="Filter by classification"
    ),
    user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> list[InboxMessageResponse]:
    """Get all inbox messages with pagination and filtering."""
    service = InboxService(db, user_id=user.id)
    messages = await service.get_all(
        skip=skip,
        limit=limit,
        status=status,
        classification=classification,
    )
    return [InboxMessageResponse.model_validate(m) for m in messages]


@router.get("/{message_id}", response_model=InboxMessageResponse)
async def get_inbox_message(
    message_id: UUID,
    user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> InboxMessageResponse:
    """Get inbox message by ID."""
    service = InboxService(db, user_id=user.id)
    message = await service.get_by_id(message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message {message_id} not found",
        )
    return InboxMessageResponse.model_validate(message)


@router.patch("/{message_id}/assign", response_model=InboxMessageResponse)
async def assign_inbox_message(
    message_id: UUID,
    assign_data: InboxAssign,
    user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> InboxMessageResponse:
    """Assign inbox message to customer and/or order."""
    service = InboxService(db, user_id=user.id)
    message = await service.assign_to(
        message_id=message_id,
        customer_id=assign_data.customer_id,
        order_id=assign_data.order_id,
    )
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message {message_id} not found",
        )
    await db.commit()
    return InboxMessageResponse.model_validate(message)


@router.patch("/{message_id}/reclassify", response_model=InboxMessageResponse)
async def reclassify_inbox_message(
    message_id: UUID,
    reclassify_data: InboxReclassify,
    user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> InboxMessageResponse:
    """Manually reclassify inbox message."""
    service = InboxService(db, user_id=user.id)
    message = await service.reclassify(
        message_id=message_id,
        new_classification=reclassify_data.classification,
    )
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message {message_id} not found",
        )
    await db.commit()
    return InboxMessageResponse.model_validate(message)
