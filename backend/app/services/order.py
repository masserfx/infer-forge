"""Order business logic service."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.metrics import orders_created_total
from app.models import AuditAction, AuditLog, Order, OrderItem, OrderStatus
from app.schemas import OrderCreate, OrderUpdate

logger = logging.getLogger(__name__)


class OrderService:
    """Service for managing orders with audit trail and status validation."""

    # Valid status transitions
    STATUS_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
        OrderStatus.POPTAVKA: [OrderStatus.NABIDKA, OrderStatus.OBJEDNAVKA],
        OrderStatus.NABIDKA: [OrderStatus.OBJEDNAVKA, OrderStatus.POPTAVKA],
        OrderStatus.OBJEDNAVKA: [OrderStatus.VYROBA],
        OrderStatus.VYROBA: [OrderStatus.EXPEDICE],
        OrderStatus.EXPEDICE: [OrderStatus.FAKTURACE],
        OrderStatus.FAKTURACE: [OrderStatus.DOKONCENO],
        OrderStatus.DOKONCENO: [],  # Final state
    }

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
            entity_type="order",
            entity_id=entity_id,
            changes=changes,
            timestamp=datetime.now(UTC),
        )
        self.db.add(audit)

    def _validate_status_transition(
        self,
        current_status: OrderStatus,
        new_status: OrderStatus,
    ) -> bool:
        """Validate if status transition is allowed.

        Args:
            current_status: Current order status
            new_status: Requested new status

        Returns:
            True if transition is valid, False otherwise
        """
        allowed_transitions = self.STATUS_TRANSITIONS.get(current_status, [])
        return new_status in allowed_transitions

    async def create(self, order_data: OrderCreate) -> Order:
        """Create a new order with items.

        Args:
            order_data: Order creation data

        Returns:
            Created order instance

        Raises:
            IntegrityError: If order number already exists
        """
        # Create order
        order_dict = order_data.model_dump(exclude={"items"})
        order_dict["created_by"] = self.user_id
        order = Order(**order_dict)
        self.db.add(order)
        await self.db.flush()

        # Create order items
        for item_data in order_data.items:
            item = OrderItem(
                order_id=order.id,
                **item_data.model_dump(),
            )
            self.db.add(item)

        await self.db.flush()
        await self.db.refresh(order)

        # Load items relationship
        await self.db.refresh(order, ["items"])

        # Audit trail (serialize UUID values to strings for JSON)
        audit_data = {k: str(v) if isinstance(v, UUID) else v for k, v in order_dict.items()}
        await self._create_audit_log(
            action=AuditAction.CREATE,
            entity_id=order.id,
            changes={
                "created": audit_data,
                "items_count": len(order_data.items),
            },
        )

        # Prometheus metric
        orders_created_total.inc()

        # Trigger embedding generation
        try:
            from app.services.embedding_tasks import generate_order_embedding

            generate_order_embedding.delay(str(order.id))
        except Exception:
            logger.warning("Failed to queue embedding generation for order %s", order.id)

        return order

    async def get_by_id(self, order_id: UUID) -> Order | None:
        """Get order by ID with related data.

        Args:
            order_id: Order UUID

        Returns:
            Order instance or None if not found
        """
        result = await self.db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items),
                selectinload(Order.customer),
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: OrderStatus | None = None,
    ) -> list[Order]:
        """Get all orders with pagination and optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Optional status filter

        Returns:
            List of order instances
        """
        query = select(Order).options(
            selectinload(Order.items),
            selectinload(Order.customer),
        )

        if status:
            query = query.where(Order.status == status)

        query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        order_id: UUID,
        order_data: OrderUpdate,
    ) -> Order | None:
        """Update order.

        Args:
            order_id: Order UUID
            order_data: Order update data

        Returns:
            Updated order instance or None if not found
        """
        order = await self.get_by_id(order_id)
        if not order:
            return None

        # Track changes for audit
        changes: dict = {}
        update_data = order_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            old_value = getattr(order, field)
            if old_value != value:
                changes[field] = {"old": str(old_value), "new": str(value)}
                setattr(order, field, value)

        if changes:
            await self.db.flush()
            await self.db.refresh(order)

            # Audit trail
            await self._create_audit_log(
                action=AuditAction.UPDATE,
                entity_id=order.id,
                changes=changes,
            )

        return order

    async def change_status(
        self,
        order_id: UUID,
        new_status: OrderStatus,
    ) -> Order | None:
        """Change order status with validation.

        Args:
            order_id: Order UUID
            new_status: New status to set

        Returns:
            Updated order or None if not found

        Raises:
            ValueError: If status transition is invalid
        """
        order = await self.get_by_id(order_id)
        if not order:
            return None

        # Validate transition
        if not self._validate_status_transition(order.status, new_status):
            raise ValueError(
                f"Invalid status transition from {order.status.value} " f"to {new_status.value}"
            )

        old_status = order.status
        order.status = new_status

        await self.db.flush()
        await self.db.refresh(order)

        # Audit trail
        await self._create_audit_log(
            action=AuditAction.UPDATE,
            entity_id=order.id,
            changes={
                "status": {
                    "old": old_status.value,
                    "new": new_status.value,
                }
            },
        )

        return order

    async def delete(self, order_id: UUID) -> bool:
        """Delete order.

        Args:
            order_id: Order UUID

        Returns:
            True if deleted, False if not found
        """
        order = await self.get_by_id(order_id)
        if not order:
            return False

        # Audit trail before deletion
        await self._create_audit_log(
            action=AuditAction.DELETE,
            entity_id=order.id,
            changes={
                "deleted_number": order.number,
                "status": order.status.value,
            },
        )

        await self.db.delete(order)
        await self.db.flush()

        return True
