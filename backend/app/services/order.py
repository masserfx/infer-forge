"""Order business logic service."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.metrics import orders_created_total
from app.models import (
    AuditAction,
    AuditLog,
    Offer,
    OfferStatus,
    Order,
    OrderItem,
    OrderStatus,
    PointsAction,
)
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

        # Award gamification points
        try:
            from app.services.gamification import GamificationService

            gamification = GamificationService(self.db)
            points = gamification.calculate_order_points(old_status, new_status)
            if points > 0 and self.user_id:
                await gamification.award_points(
                    user_id=self.user_id,
                    action=PointsAction.ORDER_STATUS_CHANGE,
                    points=points,
                    description=f"Zakázka {order.number}: {old_status.value} → {new_status.value}",
                    entity_type="order",
                    entity_id=order.id,
                )
        except Exception:
            logger.warning("Failed to award points for order %s", str(order.id))

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

    async def convert_offer_to_order(self, offer_id: UUID) -> Order:
        """Convert accepted offer to a new order.

        Args:
            offer_id: Offer UUID to convert

        Returns:
            Newly created order instance

        Raises:
            ValueError: If offer not found, already converted, or not in valid status
        """
        # 1. Load offer with related order and items
        result = await self.db.execute(
            select(Offer)
            .where(Offer.id == offer_id)
            .options(
                selectinload(Offer.order).selectinload(Order.items),
                selectinload(Offer.order).selectinload(Order.customer),
            )
        )
        offer = result.scalar_one_or_none()

        if not offer:
            raise ValueError(f"Offer {offer_id} not found")

        # 2. Validate offer status
        if offer.status not in (OfferStatus.ACCEPTED, OfferStatus.SENT):
            raise ValueError(
                f"Cannot convert offer with status {offer.status.value}. "
                "Only 'accepted' or 'sent' offers can be converted."
            )

        # 3. Check if already converted
        if offer.converted_to_order_id is not None:
            raise ValueError(
                f"Offer {offer.number} already converted to order {offer.converted_to_order_id}"
            )

        # 4. Get source order details
        source_order = offer.order
        if not source_order:
            raise ValueError(f"Offer {offer_id} has no associated source order")

        # 5. Generate new order number (increment from offer number or use timestamp)
        new_order_number = f"{source_order.number}-OBJ-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

        # 6. Create new order
        new_order = Order(
            customer_id=source_order.customer_id,
            number=new_order_number,
            status=OrderStatus.OBJEDNAVKA,
            priority=source_order.priority,
            due_date=source_order.due_date,
            note=f"Vytvořeno z nabídky {offer.number} (zakázka {source_order.number})",
            created_by=self.user_id,
            source_offer_id=offer.id,
        )
        self.db.add(new_order)
        await self.db.flush()

        # 7. Copy items from source order to new order
        for source_item in source_order.items:
            new_item = OrderItem(
                order_id=new_order.id,
                name=source_item.name,
                material=source_item.material,
                quantity=source_item.quantity,
                unit=source_item.unit,
                dn=source_item.dn,
                pn=source_item.pn,
                note=source_item.note,
                drawing_url=source_item.drawing_url,
            )
            self.db.add(new_item)

        await self.db.flush()

        # 8. Update offer status and link to new order
        offer.status = OfferStatus.ACCEPTED
        offer.converted_to_order_id = new_order.id

        await self.db.flush()
        await self.db.refresh(new_order, ["items", "customer"])

        # 9. Create audit log
        await self._create_audit_log(
            action=AuditAction.CREATE,
            entity_id=new_order.id,
            changes={
                "created_from_offer": str(offer.id),
                "offer_number": offer.number,
                "source_order": str(source_order.id),
                "items_copied": len(source_order.items),
            },
        )

        # 10. Prometheus metric
        orders_created_total.inc()

        # 11. Trigger embedding generation
        try:
            from app.services.embedding_tasks import generate_order_embedding

            generate_order_embedding.delay(str(new_order.id))
        except Exception:
            logger.warning("Failed to queue embedding generation for order %s", new_order.id)

        logger.info(
            "Converted offer %s to order %s",
            offer.number,
            new_order.number,
        )

        return new_order
