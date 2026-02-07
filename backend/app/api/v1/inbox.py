"""Inbox API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models import InboxClassification, InboxStatus
from app.schemas import InboxAssign, InboxMessageResponse, InboxReclassify
from app.services import InboxService

router = APIRouter(prefix="/inbox", tags=["Inbox"])


@router.get("/", response_model=list[InboxMessageResponse])
async def get_inbox_messages(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of records"),
    status: Optional[InboxStatus] = Query(default=None, description="Filter by status"),
    classification: Optional[InboxClassification] = Query(
        default=None, description="Filter by classification"
    ),
    db: AsyncSession = Depends(get_db),
) -> list[InboxMessageResponse]:
    """Get all inbox messages with pagination and filtering.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Optional status filter
        classification: Optional classification filter
        db: Database session

    Returns:
        List of inbox messages
    """
    service = InboxService(db)
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
    db: AsyncSession = Depends(get_db),
) -> InboxMessageResponse:
    """Get inbox message by ID.

    Args:
        message_id: Message UUID
        db: Database session

    Returns:
        Inbox message details

    Raises:
        HTTPException: If message not found
    """
    service = InboxService(db)
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
    db: AsyncSession = Depends(get_db),
) -> InboxMessageResponse:
    """Assign inbox message to customer and/or order.

    Args:
        message_id: Message UUID
        assign_data: Assignment data
        db: Database session

    Returns:
        Updated inbox message

    Raises:
        HTTPException: If message not found
    """
    service = InboxService(db)
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
    db: AsyncSession = Depends(get_db),
) -> InboxMessageResponse:
    """Manually reclassify inbox message.

    Args:
        message_id: Message UUID
        reclassify_data: New classification
        db: Database session

    Returns:
        Updated inbox message

    Raises:
        HTTPException: If message not found
    """
    service = InboxService(db)
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
