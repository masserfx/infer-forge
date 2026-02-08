"""Pohoda synchronization service.

Orchestrates XML generation, validation, sending to mServer,
and recording sync results in the database.
"""

import logging
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models import AuditAction, AuditLog, Customer, Offer, Order
from app.models.calculation import Calculation, CalculationStatus
from app.models.pohoda_sync import PohodaSyncLog, SyncDirection, SyncStatus

logger = logging.getLogger(__name__)
settings = get_settings()


class PohodaService:
    """Service for synchronizing data with Pohoda accounting system."""

    def __init__(self, db: AsyncSession, user_id: UUID | None = None):
        """Initialize service.

        Args:
            db: Async database session
            user_id: ID of user performing the operation (for audit trail)
        """
        self.db = db
        self.user_id = user_id

    async def sync_customer(self, customer_id: UUID) -> PohodaSyncLog:
        """Export customer to Pohoda.

        Args:
            customer_id: Customer UUID to sync

        Returns:
            PohodaSyncLog with sync result

        Raises:
            ValueError: If customer not found
        """
        # Load customer
        result = await self.db.execute(select(Customer).where(Customer.id == customer_id))
        customer = result.scalar_one_or_none()
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        # Create sync log entry
        sync_log = PohodaSyncLog(
            entity_type="customer",
            entity_id=customer_id,
            direction=SyncDirection.EXPORT,
            status=SyncStatus.PENDING,
        )
        self.db.add(sync_log)
        await self.db.flush()

        try:
            # Import here to avoid circular imports at module level
            from app.integrations.pohoda.xml_builder import PohodaXMLBuilder

            # Build XML
            builder = PohodaXMLBuilder()
            xml_data = builder.build_customer_xml(customer)
            sync_log.xml_request = xml_data.decode("Windows-1250", errors="replace")

            # Send to mServer
            if settings.POHODA_MSERVER_URL:
                from app.integrations.pohoda.client import PohodaClient
                from app.integrations.pohoda.xml_parser import PohodaXMLParser

                async with PohodaClient(
                    base_url=settings.POHODA_MSERVER_URL,
                    ico=settings.POHODA_ICO,
                ) as client:
                    response_bytes = await client.send_xml(xml_data)

                sync_log.xml_response = response_bytes.decode("Windows-1250", errors="replace")

                # Parse response
                parsed = PohodaXMLParser.parse_response(response_bytes)
                if parsed.success and parsed.items:
                    pohoda_id = int(parsed.items[0].id) if parsed.items[0].id else None
                    sync_log.status = SyncStatus.SUCCESS
                    sync_log.pohoda_doc_number = parsed.items[0].id

                    # Update customer with Pohoda ID
                    if pohoda_id:
                        customer.pohoda_id = pohoda_id
                    customer.pohoda_synced_at = datetime.now(UTC)
                else:
                    error_notes = [item.note for item in parsed.items if item.state != "ok"]
                    sync_log.status = SyncStatus.ERROR
                    sync_log.error_message = "; ".join(error_notes) or "Unknown error"
            else:
                # No mServer URL configured - mark as success for dry run
                sync_log.status = SyncStatus.SUCCESS
                logger.warning(
                    "pohoda_mserver_not_configured entity_type=customer entity_id=%s",
                    str(customer_id),
                )

        except Exception as e:
            sync_log.status = SyncStatus.ERROR
            sync_log.error_message = str(e)
            logger.error(
                "pohoda_sync_failed entity_type=customer entity_id=%s error=%s",
                str(customer_id),
                str(e),
            )

        await self.db.flush()
        await self._create_audit_log(
            action=AuditAction.UPDATE,
            entity_type="customer",
            entity_id=customer_id,
            changes={
                "pohoda_sync": {
                    "direction": "export",
                    "status": sync_log.status.value,
                    "error": sync_log.error_message,
                }
            },
        )
        return sync_log

    async def sync_order(self, order_id: UUID) -> PohodaSyncLog:
        """Export order to Pohoda.

        Args:
            order_id: Order UUID to sync

        Returns:
            PohodaSyncLog with sync result

        Raises:
            ValueError: If order not found
        """
        # Load order with customer
        result = await self.db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.customer),
                selectinload(Order.items),
            )
        )
        order = result.scalar_one_or_none()
        if not order:
            raise ValueError(f"Order {order_id} not found")

        # Create sync log entry
        sync_log = PohodaSyncLog(
            entity_type="order",
            entity_id=order_id,
            direction=SyncDirection.EXPORT,
            status=SyncStatus.PENDING,
        )
        self.db.add(sync_log)
        await self.db.flush()

        try:
            from app.integrations.pohoda.xml_builder import PohodaXMLBuilder

            builder = PohodaXMLBuilder()
            xml_data = builder.build_order_xml(order, order.customer)
            sync_log.xml_request = xml_data.decode("Windows-1250", errors="replace")

            if settings.POHODA_MSERVER_URL:
                from app.integrations.pohoda.client import PohodaClient
                from app.integrations.pohoda.xml_parser import PohodaXMLParser

                async with PohodaClient(
                    base_url=settings.POHODA_MSERVER_URL,
                    ico=settings.POHODA_ICO,
                ) as client:
                    response_bytes = await client.send_xml(xml_data)

                sync_log.xml_response = response_bytes.decode("Windows-1250", errors="replace")

                parsed = PohodaXMLParser.parse_response(response_bytes)
                if parsed.success and parsed.items:
                    pohoda_id = int(parsed.items[0].id) if parsed.items[0].id else None
                    sync_log.status = SyncStatus.SUCCESS
                    sync_log.pohoda_doc_number = parsed.items[0].id

                    if pohoda_id:
                        order.pohoda_id = pohoda_id
                    order.pohoda_synced_at = datetime.now(UTC)
                else:
                    error_notes = [item.note for item in parsed.items if item.state != "ok"]
                    sync_log.status = SyncStatus.ERROR
                    sync_log.error_message = "; ".join(error_notes) or "Unknown error"
            else:
                sync_log.status = SyncStatus.SUCCESS
                logger.warning(
                    "pohoda_mserver_not_configured entity_type=order entity_id=%s",
                    str(order_id),
                )

        except Exception as e:
            sync_log.status = SyncStatus.ERROR
            sync_log.error_message = str(e)
            logger.error(
                "pohoda_sync_failed entity_type=order entity_id=%s error=%s",
                str(order_id),
                str(e),
            )

        await self.db.flush()
        await self._create_audit_log(
            action=AuditAction.UPDATE,
            entity_type="order",
            entity_id=order_id,
            changes={
                "pohoda_sync": {
                    "direction": "export",
                    "status": sync_log.status.value,
                    "error": sync_log.error_message,
                }
            },
        )
        return sync_log

    async def sync_offer(self, offer_id: UUID) -> PohodaSyncLog:
        """Export offer to Pohoda.

        Args:
            offer_id: Offer UUID to sync

        Returns:
            PohodaSyncLog with sync result

        Raises:
            ValueError: If offer not found
        """
        # Load offer with order and customer
        result = await self.db.execute(
            select(Offer)
            .where(Offer.id == offer_id)
            .options(selectinload(Offer.order).selectinload(Order.customer))
        )
        offer = result.scalar_one_or_none()
        if not offer:
            raise ValueError(f"Offer {offer_id} not found")

        sync_log = PohodaSyncLog(
            entity_type="offer",
            entity_id=offer_id,
            direction=SyncDirection.EXPORT,
            status=SyncStatus.PENDING,
        )
        self.db.add(sync_log)
        await self.db.flush()

        try:
            from app.integrations.pohoda.xml_builder import PohodaXMLBuilder

            builder = PohodaXMLBuilder()
            xml_data = builder.build_offer_xml(offer, offer.order, offer.order.customer)
            sync_log.xml_request = xml_data.decode("Windows-1250", errors="replace")

            if settings.POHODA_MSERVER_URL:
                from app.integrations.pohoda.client import PohodaClient
                from app.integrations.pohoda.xml_parser import PohodaXMLParser

                async with PohodaClient(
                    base_url=settings.POHODA_MSERVER_URL,
                    ico=settings.POHODA_ICO,
                ) as client:
                    response_bytes = await client.send_xml(xml_data)

                sync_log.xml_response = response_bytes.decode("Windows-1250", errors="replace")

                parsed = PohodaXMLParser.parse_response(response_bytes)
                if parsed.success and parsed.items:
                    pohoda_id = int(parsed.items[0].id) if parsed.items[0].id else None
                    sync_log.status = SyncStatus.SUCCESS
                    sync_log.pohoda_doc_number = parsed.items[0].id

                    if pohoda_id:
                        offer.pohoda_id = pohoda_id
                else:
                    error_notes = [item.note for item in parsed.items if item.state != "ok"]
                    sync_log.status = SyncStatus.ERROR
                    sync_log.error_message = "; ".join(error_notes) or "Unknown error"
            else:
                sync_log.status = SyncStatus.SUCCESS
                logger.warning(
                    "pohoda_mserver_not_configured entity_type=offer entity_id=%s",
                    str(offer_id),
                )

        except Exception as e:
            sync_log.status = SyncStatus.ERROR
            sync_log.error_message = str(e)
            logger.error(
                "pohoda_sync_failed entity_type=offer entity_id=%s error=%s",
                str(offer_id),
                str(e),
            )

        await self.db.flush()
        await self._create_audit_log(
            action=AuditAction.UPDATE,
            entity_type="offer",
            entity_id=offer_id,
            changes={
                "pohoda_sync": {
                    "direction": "export",
                    "status": sync_log.status.value,
                    "error": sync_log.error_message,
                }
            },
        )
        return sync_log

    async def get_sync_status(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> dict[str, object]:
        """Get sync status for an entity.

        Args:
            entity_type: Entity type (customer, order, offer)
            entity_id: Entity UUID

        Returns:
            Dict with sync status info
        """
        # Get last sync log
        result = await self.db.execute(
            select(PohodaSyncLog)
            .where(
                PohodaSyncLog.entity_type == entity_type,
                PohodaSyncLog.entity_id == entity_id,
            )
            .order_by(PohodaSyncLog.synced_at.desc())
            .limit(1)
        )
        last_sync = result.scalar_one_or_none()

        # Count total syncs
        count_result = await self.db.execute(
            select(func.count())
            .select_from(PohodaSyncLog)
            .where(
                PohodaSyncLog.entity_type == entity_type,
                PohodaSyncLog.entity_id == entity_id,
            )
        )
        sync_count = count_result.scalar() or 0

        # Get last successful sync
        success_result = await self.db.execute(
            select(PohodaSyncLog.synced_at)
            .where(
                PohodaSyncLog.entity_type == entity_type,
                PohodaSyncLog.entity_id == entity_id,
                PohodaSyncLog.status == SyncStatus.SUCCESS,
            )
            .order_by(PohodaSyncLog.synced_at.desc())
            .limit(1)
        )
        last_success = success_result.scalar_one_or_none()

        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "last_sync": last_sync,
            "sync_count": sync_count,
            "last_success": last_success,
        }

    async def get_sync_logs(
        self,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        status: SyncStatus | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[PohodaSyncLog]:
        """Get sync logs with optional filtering.

        Args:
            entity_type: Optional entity type filter
            entity_id: Optional entity ID filter
            status: Optional status filter
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of sync log entries
        """
        query = select(PohodaSyncLog)

        if entity_type:
            query = query.where(PohodaSyncLog.entity_type == entity_type)
        if entity_id:
            query = query.where(PohodaSyncLog.entity_id == entity_id)
        if status:
            query = query.where(PohodaSyncLog.status == status)

        query = query.order_by(PohodaSyncLog.synced_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def generate_invoice(
        self,
        order_id: UUID,
        invoice_number: str,
        invoice_date: date | None = None,
        due_days: int = 14,
        invoice_type: str = "final",
        advance_percent: int = 50,
    ) -> PohodaSyncLog:
        """Generate invoice XML for an order and send to Pohoda.

        Args:
            order_id: Order UUID to generate invoice for
            invoice_number: Invoice number (e.g., "FV-2025-001")
            invoice_date: Invoice issue date (defaults to today)
            due_days: Payment due in days (default 14)
            invoice_type: Type of invoice - "final", "advance", or "proforma"
            advance_percent: Percentage of advance payment (10-90, default 50). Only for "advance" type.

        Returns:
            PohodaSyncLog with sync result

        Raises:
            ValueError: If order not found
        """
        # Load order with items and customer
        result = await self.db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.customer),
                selectinload(Order.items),
            )
        )
        order = result.scalar_one_or_none()
        if not order:
            raise ValueError(f"Order {order_id} not found")

        # Create sync log entry
        sync_log = PohodaSyncLog(
            entity_type="invoice",
            entity_id=order_id,
            direction=SyncDirection.EXPORT,
            status=SyncStatus.PENDING,
        )
        self.db.add(sync_log)
        await self.db.flush()

        try:
            # Lookup latest approved calculation for pricing (with items loaded)
            calc_result = await self.db.execute(
                select(Calculation)
                .where(Calculation.order_id == order.id)
                .where(Calculation.status == CalculationStatus.APPROVED)
                .options(selectinload(Calculation.items))
                .order_by(Calculation.updated_at.desc())
                .limit(1)
            )
            calculation = calc_result.scalar_one_or_none()

            if calculation:
                logger.info(
                    "invoice_using_calculation invoice_number=%s order_id=%s calculation_id=%s total_price=%s",
                    invoice_number,
                    str(order_id),
                    str(calculation.id),
                    str(calculation.total_price),
                )
            else:
                logger.warning(
                    "invoice_no_approved_calculation invoice_number=%s order_id=%s",
                    invoice_number,
                    str(order_id),
                )

            from app.integrations.pohoda.xml_builder import PohodaXMLBuilder

            builder = PohodaXMLBuilder()
            xml_data = builder.build_invoice_xml(
                order=order,
                customer=order.customer,
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                due_days=due_days,
                calculation=calculation,
                invoice_type=invoice_type,
                advance_percent=advance_percent,
            )
            sync_log.xml_request = xml_data.decode("Windows-1250", errors="replace")

            if settings.POHODA_MSERVER_URL:
                from app.integrations.pohoda.client import PohodaClient
                from app.integrations.pohoda.xml_parser import PohodaXMLParser

                async with PohodaClient(
                    base_url=settings.POHODA_MSERVER_URL,
                    ico=settings.POHODA_ICO,
                ) as client:
                    response_bytes = await client.send_xml(xml_data)

                sync_log.xml_response = response_bytes.decode("Windows-1250", errors="replace")

                parsed = PohodaXMLParser.parse_response(response_bytes)
                if parsed.success and parsed.items:
                    sync_log.status = SyncStatus.SUCCESS
                    sync_log.pohoda_doc_number = parsed.items[0].id

                    # Update order with invoice sync timestamp
                    order.pohoda_synced_at = datetime.now(UTC)
                else:
                    error_notes = [item.note for item in parsed.items if item.state != "ok"]
                    sync_log.status = SyncStatus.ERROR
                    sync_log.error_message = "; ".join(error_notes) or "Unknown error"
            else:
                sync_log.status = SyncStatus.SUCCESS
                logger.warning(
                    "pohoda_mserver_not_configured entity_type=invoice entity_id=%s",
                    str(order_id),
                )

        except Exception as e:
            sync_log.status = SyncStatus.ERROR
            sync_log.error_message = str(e)
            logger.error(
                "pohoda_sync_failed entity_type=invoice entity_id=%s error=%s",
                str(order_id),
                str(e),
            )

        await self.db.flush()
        await self._create_audit_log(
            action=AuditAction.CREATE,
            entity_type="invoice",
            entity_id=order_id,
            changes={
                "pohoda_invoice": {
                    "invoice_number": invoice_number,
                    "direction": "export",
                    "status": sync_log.status.value,
                    "error": sync_log.error_message,
                }
            },
        )
        return sync_log

    async def _create_audit_log(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: UUID,
        changes: dict[str, object] | None = None,
    ) -> None:
        """Create audit log entry for sync operation."""
        audit = AuditLog(
            user_id=self.user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes,
            timestamp=datetime.now(UTC),
        )
        self.db.add(audit)

    async def sync_inventory(self) -> dict[str, int]:
        """Sync Pohoda stock cards to MaterialPrice table.

        Returns:
            Summary: {synced, created, updated, errors}
        """
        from app.integrations.pohoda.client import PohodaClient
        from app.integrations.pohoda.stock_parser import PohodaStockParser
        from app.integrations.pohoda.xml_builder import PohodaXMLBuilder
        from app.models.material_price import MaterialPrice

        builder = PohodaXMLBuilder()
        request_xml = builder.build_stock_list_request()

        async with PohodaClient(
            base_url=settings.POHODA_MSERVER_URL,
            ico=settings.POHODA_ICO,
        ) as client:
            response_xml = await client.send_xml(request_xml)

        parser = PohodaStockParser()
        stock_items = parser.parse_stock_list(response_xml)

        results = {"synced": 0, "created": 0, "updated": 0, "errors": 0}
        today = date.today()

        for item in stock_items:
            try:
                result = await self.db.execute(
                    select(MaterialPrice).where(
                        MaterialPrice.name == item.name,
                        MaterialPrice.is_active.is_(True),
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    existing.unit_price = item.purchasing_price
                    existing.unit = item.unit
                    if item.supplier:
                        existing.supplier = item.supplier
                    if item.note:
                        existing.specification = item.note
                    results["updated"] += 1
                else:
                    new_price = MaterialPrice(
                        name=item.name,
                        specification=item.note,
                        unit=item.unit,
                        unit_price=item.purchasing_price,
                        supplier=item.supplier,
                        valid_from=today,
                        is_active=True,
                    )
                    self.db.add(new_price)
                    results["created"] += 1

                results["synced"] += 1
            except Exception as e:
                logger.error("Failed to sync item %s: %s", item.code, str(e))
                results["errors"] += 1

        await self.db.commit()
        return results
