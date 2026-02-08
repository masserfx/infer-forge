"""Inbox business logic service."""

import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditAction,
    AuditLog,
    Customer,
    InboxClassification,
    InboxMessage,
    InboxStatus,
    Order,
    OrderStatus,
)


class InboxService:
    """Service for managing inbox messages with audit trail."""

    def __init__(self, db: AsyncSession, user_id: UUID | None = None):
        """Initialize service.

        Args:
            db: Async database session
            user_id: ID of user performing the operation (for audit trail)
        """
        self.db = db
        self.user_id = user_id

    async def _create_audit_log(
        self,
        action: AuditAction,
        entity_id: UUID,
        changes: dict | None = None,
    ) -> None:
        """Create audit log entry.

        Args:
            action: Audit action type
            entity_id: ID of affected entity
            changes: Dictionary of changes made
        """
        audit = AuditLog(
            user_id=self.user_id,
            action=action,
            entity_type="inbox_message",
            entity_id=entity_id,
            changes=changes,
            timestamp=datetime.now(UTC),
        )
        self.db.add(audit)

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: InboxStatus | None = None,
        classification: InboxClassification | None = None,
    ) -> list[InboxMessage]:
        """Get all inbox messages with pagination and filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Optional status filter
            classification: Optional classification filter

        Returns:
            List of inbox message instances
        """
        query = select(InboxMessage)

        if status:
            query = query.where(InboxMessage.status == status)
        if classification:
            query = query.where(InboxMessage.classification == classification)

        query = query.order_by(InboxMessage.received_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, message_id: UUID) -> InboxMessage | None:
        """Get inbox message by ID.

        Args:
            message_id: Message UUID

        Returns:
            InboxMessage instance or None if not found
        """
        result = await self.db.execute(select(InboxMessage).where(InboxMessage.id == message_id))
        return result.scalar_one_or_none()

    async def assign_to(
        self,
        message_id: UUID,
        customer_id: UUID | None = None,
        order_id: UUID | None = None,
    ) -> InboxMessage | None:
        """Assign inbox message to customer and/or order.

        Args:
            message_id: Message UUID
            customer_id: Optional customer UUID to assign
            order_id: Optional order UUID to assign

        Returns:
            Updated message or None if not found
        """
        message = await self.get_by_id(message_id)
        if not message:
            return None

        changes: dict = {}

        if customer_id is not None:
            old_customer = message.customer_id
            message.customer_id = customer_id
            changes["customer_id"] = {
                "old": str(old_customer) if old_customer else None,
                "new": str(customer_id),
            }

        if order_id is not None:
            old_order = message.order_id
            message.order_id = order_id
            changes["order_id"] = {
                "old": str(old_order) if old_order else None,
                "new": str(order_id),
            }

        # Update status if assigned
        if customer_id or order_id:
            old_status = message.status
            message.status = InboxStatus.PROCESSING
            changes["status"] = {
                "old": old_status.value,
                "new": InboxStatus.PROCESSING.value,
            }

        if changes:
            await self.db.flush()
            await self.db.refresh(message)

            # Audit trail
            await self._create_audit_log(
                action=AuditAction.UPDATE,
                entity_id=message.id,
                changes=changes,
            )

        return message

    async def reclassify(
        self,
        message_id: UUID,
        new_classification: InboxClassification,
    ) -> InboxMessage | None:
        """Reclassify inbox message.

        Args:
            message_id: Message UUID
            new_classification: New classification

        Returns:
            Updated message or None if not found
        """
        message = await self.get_by_id(message_id)
        if not message:
            return None

        old_classification = message.classification
        message.classification = new_classification
        message.confidence = None  # Reset confidence since this is manual reclassification

        await self.db.flush()
        await self.db.refresh(message)

        # Audit trail
        await self._create_audit_log(
            action=AuditAction.UPDATE,
            entity_id=message.id,
            changes={
                "classification": {
                    "old": old_classification.value if old_classification else None,
                    "new": new_classification.value,
                },
                "confidence": {"old": message.confidence, "new": None},
                "reclassified_manually": True,
            },
        )

        return message


async def match_email_to_order(
    db: AsyncSession,
    inbox_message: InboxMessage,
) -> UUID | None:
    """Match inbox message to an order based on order number or sender email.

    Matching strategy:
    1. Search for order number in subject and body using regex patterns
    2. If not found, search by sender email → Customer → active orders
    3. Return first matching order_id or None

    Args:
        db: Async database session
        inbox_message: InboxMessage instance to match

    Returns:
        UUID of matched order, or None if no match found
    """
    # Pattern 1: Standard format ZAK-2024-001, ZAK-2025-123
    # Pattern 2: Custom prefix NAB-2024-005, OBJ-2024-100, etc.
    order_patterns = [
        r"ZAK-\d{4}-\d{3,}",  # ZAK-2024-001
        r"[A-Z]{2,3}-\d{4}-\d{3,}",  # NAB-2024-005, OBJ-2025-100
    ]

    # Search in subject first
    text_to_search = f"{inbox_message.subject} {inbox_message.body_text}"

    for pattern in order_patterns:
        match = re.search(pattern, text_to_search)
        if match:
            order_number = match.group(0)

            # Look up order in database
            result = await db.execute(
                select(Order).where(Order.number == order_number)
            )
            order = result.scalar_one_or_none()

            if order:
                return order.id

    # Strategy 2: Match by sender email → Customer → active orders
    result = await db.execute(
        select(Customer).where(Customer.email == inbox_message.from_email)
    )
    customer = result.scalar_one_or_none()

    if customer:
        # Get customer's most recent active order (not DOKONCENO)
        result = await db.execute(
            select(Order)
            .where(
                Order.customer_id == customer.id,
                Order.status != OrderStatus.DOKONCENO,
            )
            .order_by(Order.created_at.desc())
            .limit(1)
        )
        active_order = result.scalar_one_or_none()

        if active_order:
            return active_order.id

    # No match found
    return None
