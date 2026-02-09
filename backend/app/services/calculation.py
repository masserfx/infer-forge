"""Calculation business logic service."""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    AuditAction,
    AuditLog,
    Calculation,
    CalculationItem,
    CalculationStatus,
    CostType,
    Offer,
    OfferStatus,
    Order,
    OrderStatus,
)
from app.schemas import (
    CalculationCreate,
    CalculationItemCreate,
    CalculationItemUpdate,
    CalculationUpdate,
)

logger = logging.getLogger(__name__)


class CalculationService:
    """Service for managing calculations with automatic totals recalculation."""

    def __init__(self, db: AsyncSession, user_id: UUID | None = None):
        self.db = db
        self.user_id = user_id

    async def _create_audit_log(
        self,
        action: AuditAction,
        entity_id: UUID,
        changes: dict | None = None,
    ) -> None:
        audit = AuditLog(
            user_id=self.user_id,
            action=action,
            entity_type="calculation",
            entity_id=entity_id,
            changes=changes,
            timestamp=datetime.now(UTC),
        )
        self.db.add(audit)

    def _recalculate_totals(self, calculation: Calculation) -> None:
        """Recalculate all totals from items, including customer discount.

        Calculation flow:
        1. Sum items by cost_type
        2. Calculate subtotal (material + labor + cooperation + overhead)
        3. Apply margin percentage
        4. Apply customer discount (if any)
        5. Final total_price
        """
        material = Decimal("0")
        labor = Decimal("0")
        cooperation = Decimal("0")
        overhead = Decimal("0")

        for item in calculation.items:
            item.total_price = item.quantity * item.unit_price

            if item.cost_type == CostType.MATERIAL:
                material += item.total_price
            elif item.cost_type == CostType.LABOR:
                labor += item.total_price
            elif item.cost_type == CostType.COOPERATION:
                cooperation += item.total_price
            elif item.cost_type == CostType.OVERHEAD:
                overhead += item.total_price

        calculation.material_total = material
        calculation.labor_total = labor
        calculation.cooperation_total = cooperation
        calculation.overhead_total = overhead

        subtotal = material + labor + cooperation + overhead
        calculation.margin_amount = (
            subtotal * calculation.margin_percent / Decimal("100")
        ).quantize(Decimal("0.01"))

        # Total before customer discount
        price_before_discount = subtotal + calculation.margin_amount

        # Apply customer discount if available
        customer_discount = Decimal("0.00")
        if calculation.order and calculation.order.customer:
            customer = calculation.order.customer
            if customer.discount_percent and customer.discount_percent > 0:
                customer_discount = (
                    price_before_discount * customer.discount_percent / Decimal("100")
                ).quantize(Decimal("0.01"))

        calculation.total_price = price_before_discount - customer_discount

    async def create(self, data: CalculationCreate) -> Calculation:
        """Create a new calculation with optional initial items."""
        calculation = Calculation(
            order_id=data.order_id,
            name=data.name,
            note=data.note,
            margin_percent=data.margin_percent,
            created_by=self.user_id,
        )
        self.db.add(calculation)
        await self.db.flush()

        # Add initial items
        for item_data in data.items:
            item = CalculationItem(
                calculation_id=calculation.id,
                cost_type=item_data.cost_type,
                name=item_data.name,
                description=item_data.description,
                quantity=item_data.quantity,
                unit=item_data.unit,
                unit_price=item_data.unit_price,
                total_price=item_data.quantity * item_data.unit_price,
            )
            self.db.add(item)

        await self.db.flush()
        await self.db.refresh(calculation, ["items"])

        # Recalculate totals
        self._recalculate_totals(calculation)
        await self.db.flush()
        await self.db.refresh(calculation)

        # Audit trail
        await self._create_audit_log(
            action=AuditAction.CREATE,
            entity_id=calculation.id,
            changes={
                "name": data.name,
                "order_id": str(data.order_id),
                "margin_percent": str(data.margin_percent),
                "items_count": len(data.items),
                "total_price": str(calculation.total_price),
            },
        )

        logger.info(
            "calculation_created id=%s order_id=%s total=%s",
            calculation.id,
            data.order_id,
            calculation.total_price,
        )

        return calculation

    async def get_by_id(self, calculation_id: UUID) -> Calculation | None:
        """Get calculation by ID with items and customer (for discount calculation)."""
        from app.models import Order

        result = await self.db.execute(
            select(Calculation)
            .where(Calculation.id == calculation_id)
            .options(
                selectinload(Calculation.items),
                selectinload(Calculation.order).selectinload(Order.customer),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_order(self, order_id: UUID) -> list[Calculation]:
        """Get all calculations for an order with customer data."""
        from app.models import Order

        result = await self.db.execute(
            select(Calculation)
            .where(Calculation.order_id == order_id)
            .options(
                selectinload(Calculation.items),
                selectinload(Calculation.order).selectinload(Order.customer),
            )
            .order_by(Calculation.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_all(
        self,
        status: CalculationStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Calculation]:
        """Get all calculations with optional status filter and customer data."""
        from app.models import Order

        query = select(Calculation).options(
            selectinload(Calculation.items),
            selectinload(Calculation.order).selectinload(Order.customer),
        )

        if status:
            query = query.where(Calculation.status == status)

        query = query.order_by(Calculation.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        calculation_id: UUID,
        data: CalculationUpdate,
    ) -> Calculation | None:
        """Update calculation metadata (name, note, margin, status)."""
        calculation = await self.get_by_id(calculation_id)
        if not calculation:
            return None

        old_status = calculation.status
        changes: dict = {}
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            old_value = getattr(calculation, field)
            old_str = old_value.value if hasattr(old_value, "value") else str(old_value)
            new_str = value.value if hasattr(value, "value") else str(value)
            if old_str != new_str:
                changes[field] = {"old": old_str, "new": new_str}
                setattr(calculation, field, value)

        # Recalculate if margin changed
        if "margin_percent" in update_data:
            self._recalculate_totals(calculation)
            changes["total_price"] = str(calculation.total_price)

        if changes:
            await self.db.flush()
            await self.db.refresh(calculation, ["items"])

            await self._create_audit_log(
                action=AuditAction.UPDATE,
                entity_id=calculation.id,
                changes=changes,
            )

        # Trigger offer generation when status changes to APPROVED
        if (
            old_status != CalculationStatus.APPROVED
            and calculation.status == CalculationStatus.APPROVED
            and calculation.order_id
        ):
            self._trigger_offer_generation(calculation)

        return calculation

    @staticmethod
    def _trigger_offer_generation(calculation: Calculation) -> None:
        """Dispatch Celery task to generate offer PDF + Pohoda XML."""
        try:
            from app.core.celery_app import celery_app

            celery_app.send_task(
                "orchestration.generate_offer",
                args=[{
                    "order_id": str(calculation.order_id),
                    "calculation_id": str(calculation.id),
                }],
            )
            logger.info(
                "offer_generation_triggered calculation_id=%s order_id=%s",
                calculation.id,
                calculation.order_id,
            )
        except Exception:
            logger.warning(
                "offer_generation_trigger_failed calculation_id=%s",
                calculation.id,
            )

    async def add_item(
        self,
        calculation_id: UUID,
        item_data: CalculationItemCreate,
    ) -> Calculation | None:
        """Add an item to a calculation and recalculate totals."""
        calculation = await self.get_by_id(calculation_id)
        if not calculation:
            return None

        item = CalculationItem(
            calculation_id=calculation_id,
            cost_type=item_data.cost_type,
            name=item_data.name,
            description=item_data.description,
            quantity=item_data.quantity,
            unit=item_data.unit,
            unit_price=item_data.unit_price,
            total_price=item_data.quantity * item_data.unit_price,
        )
        self.db.add(item)
        await self.db.flush()

        await self.db.refresh(calculation, ["items"])
        self._recalculate_totals(calculation)
        await self.db.flush()
        await self.db.refresh(calculation)

        await self._create_audit_log(
            action=AuditAction.UPDATE,
            entity_id=calculation.id,
            changes={
                "added_item": item_data.name,
                "cost_type": item_data.cost_type.value,
                "total_price": str(calculation.total_price),
            },
        )

        return calculation

    async def update_item(
        self,
        calculation_id: UUID,
        item_id: UUID,
        item_data: CalculationItemUpdate,
    ) -> Calculation | None:
        """Update a calculation item and recalculate totals."""
        calculation = await self.get_by_id(calculation_id)
        if not calculation:
            return None

        # Find the item
        item = None
        for i in calculation.items:
            if i.id == item_id:
                item = i
                break

        if not item:
            return None

        changes: dict = {}
        for field, value in item_data.model_dump(exclude_unset=True).items():
            old_value = getattr(item, field)
            old_str = old_value.value if hasattr(old_value, "value") else str(old_value)
            new_str = value.value if hasattr(value, "value") else str(value)
            if old_str != new_str:
                changes[field] = {"old": old_str, "new": new_str}
                setattr(item, field, value)

        self._recalculate_totals(calculation)
        await self.db.flush()
        await self.db.refresh(calculation, ["items"])

        if changes:
            await self._create_audit_log(
                action=AuditAction.UPDATE,
                entity_id=calculation.id,
                changes={
                    "updated_item": str(item_id),
                    "item_changes": changes,
                    "total_price": str(calculation.total_price),
                },
            )

        return calculation

    async def remove_item(
        self,
        calculation_id: UUID,
        item_id: UUID,
    ) -> Calculation | None:
        """Remove an item from a calculation and recalculate totals."""
        calculation = await self.get_by_id(calculation_id)
        if not calculation:
            return None

        # Find and remove the item
        item = None
        for i in calculation.items:
            if i.id == item_id:
                item = i
                break

        if not item:
            return None

        item_name = item.name
        await self.db.delete(item)
        await self.db.flush()

        await self.db.refresh(calculation, ["items"])
        self._recalculate_totals(calculation)
        await self.db.flush()
        await self.db.refresh(calculation)

        await self._create_audit_log(
            action=AuditAction.UPDATE,
            entity_id=calculation.id,
            changes={
                "removed_item": item_name,
                "item_id": str(item_id),
                "total_price": str(calculation.total_price),
            },
        )

        return calculation

    async def _generate_next_offer_number(self) -> str:
        """Generate next sequential offer number (NAB-XXXXXX)."""
        result = await self.db.execute(
            select(Offer).order_by(Offer.created_at.desc()).limit(1)
        )
        last_offer = result.scalar_one_or_none()

        if last_offer:
            try:
                last_num = int(last_offer.number.split("-")[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1

        return f"NAB-{next_num:06d}"

    async def generate_offer(
        self,
        calculation_id: UUID,
        offer_number: str | None = None,
        valid_days: int = 30,
    ) -> Offer | None:
        """Generate an Offer from a calculation."""
        from datetime import timedelta

        calculation = await self.get_by_id(calculation_id)
        if not calculation:
            return None

        if calculation.total_price <= 0:
            raise ValueError("Cannot generate offer from empty calculation")

        if not offer_number:
            offer_number = await self._generate_next_offer_number()

        valid_until = datetime.now(UTC).date() + timedelta(days=valid_days)

        offer = Offer(
            order_id=calculation.order_id,
            number=offer_number,
            total_price=calculation.total_price,
            valid_until=valid_until,
            status=OfferStatus.DRAFT,
        )
        self.db.add(offer)

        # Mark calculation as offered
        calculation.status = CalculationStatus.OFFERED

        # Advance order status to NABIDKA if currently POPTAVKA
        if calculation.order_id:
            order = await self.db.get(Order, calculation.order_id)
            if order and order.status == OrderStatus.POPTAVKA:
                order.status = OrderStatus.NABIDKA

        await self.db.flush()
        await self.db.refresh(offer)

        await self._create_audit_log(
            action=AuditAction.CREATE,
            entity_id=calculation.id,
            changes={
                "generated_offer": offer_number,
                "offer_id": str(offer.id),
                "total_price": str(calculation.total_price),
                "valid_until": str(valid_until),
            },
        )

        logger.info(
            "offer_generated calculation_id=%s offer_number=%s total=%s",
            calculation_id,
            offer_number,
            calculation.total_price,
        )

        return offer

    async def delete(self, calculation_id: UUID) -> bool:
        """Delete a calculation."""
        calculation = await self.get_by_id(calculation_id)
        if not calculation:
            return False

        await self._create_audit_log(
            action=AuditAction.DELETE,
            entity_id=calculation.id,
            changes={
                "deleted_name": calculation.name,
                "order_id": str(calculation.order_id),
                "total_price": str(calculation.total_price),
            },
        )

        await self.db.delete(calculation)
        await self.db.flush()

        return True
