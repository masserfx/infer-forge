"""Celery tasks for Pohoda synchronization."""

import asyncio
import logging
from uuid import UUID

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


def _run_async(coro):  # type: ignore[no-untyped-def]
    """Run an async coroutine from sync Celery task context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_entity_task(self, entity_type: str, entity_id: str) -> dict:  # type: ignore[no-untyped-def]
    """Async Celery task to sync an entity with Pohoda.

    Args:
        entity_type: Entity type (customer, order, offer)
        entity_id: Entity UUID string

    Returns:
        Dict with sync result
    """
    logger.info(
        "pohoda_sync_task_started entity_type=%s entity_id=%s",
        entity_type,
        entity_id,
    )

    async def _sync() -> dict:
        from app.services.pohoda import PohodaService

        async with AsyncSessionLocal() as session:
            service = PohodaService(session)
            uid = UUID(entity_id)

            try:
                if entity_type == "customer":
                    sync_log = await service.sync_customer(uid)
                elif entity_type == "order":
                    sync_log = await service.sync_order(uid)
                elif entity_type == "offer":
                    sync_log = await service.sync_offer(uid)
                else:
                    return {"success": False, "error": f"Unknown entity type: {entity_type}"}

                await session.commit()

                # Prometheus metric
                try:
                    from app.core.metrics import pohoda_sync_total

                    pohoda_sync_total.labels(status=sync_log.status.value).inc()
                except Exception:
                    logger.warning("pohoda_sync_metrics_failed entity_type=%s", entity_type)

                # Emit persisted notification via NotificationService
                try:
                    from app.models.notification import NotificationType
                    from app.models.user import UserRole
                    from app.services.notification import NotificationService

                    notif_service = NotificationService(session)
                    await notif_service.create_for_roles(
                        notification_type=NotificationType.POHODA_SYNC_COMPLETE,
                        title="Synchronizace Pohoda",
                        message=f"{entity_type} {'úspěšně synchronizován' if sync_log.status.value == 'success' else 'chyba synchronizace'}",
                        roles=[UserRole.ADMIN, UserRole.UCETNI, UserRole.VEDENI],
                        link="/pohoda",
                    )
                    await session.commit()
                except Exception:
                    logger.warning("pohoda_sync_notification_failed entity_type=%s", entity_type)

                return {
                    "success": sync_log.status.value == "success",
                    "sync_log_id": str(sync_log.id),
                    "status": sync_log.status.value,
                    "error": sync_log.error_message,
                }
            except Exception as e:
                await session.rollback()
                logger.error(
                    "pohoda_sync_task_failed entity_type=%s entity_id=%s error=%s",
                    entity_type,
                    entity_id,
                    str(e),
                )
                raise self.retry(exc=e) from e

    return _run_async(_sync())


@celery_app.task
def sync_daily_exports() -> dict:  # type: ignore[no-untyped-def]
    """Daily scheduled task to sync unsynced entities to Pohoda.

    Finds entities without pohoda_synced_at and syncs them.

    Returns:
        Dict with sync summary
    """
    logger.info("pohoda_daily_sync_started")

    async def _daily_sync() -> dict:
        from sqlalchemy import select

        from app.models import Customer, Order

        results = {"customers": 0, "orders": 0, "errors": 0}

        async with AsyncSessionLocal() as session:
            # Find unsynced customers
            customer_result = await session.execute(
                select(Customer.id).where(Customer.pohoda_synced_at.is_(None))
            )
            customer_ids = [row[0] for row in customer_result.all()]

            # Find unsynced orders
            order_result = await session.execute(
                select(Order.id).where(Order.pohoda_synced_at.is_(None))
            )
            order_ids = [row[0] for row in order_result.all()]

        # Queue individual sync tasks
        for cid in customer_ids:
            sync_entity_task.delay("customer", str(cid))
            results["customers"] += 1

        for oid in order_ids:
            sync_entity_task.delay("order", str(oid))
            results["orders"] += 1

        logger.info(
            "pohoda_daily_sync_queued",
            customers=results["customers"],
            orders=results["orders"],
        )
        return results

    return _run_async(_daily_sync())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def sync_inventory_from_pohoda(self) -> dict:  # type: ignore[no-untyped-def]
    """Import material prices from Pohoda stock cards.

    Returns:
        Summary dict with synced/created/updated/errors counts
    """
    logger.info("pohoda_inventory_sync_started")

    async def _sync() -> dict:
        from datetime import date

        from sqlalchemy import select

        from app.integrations.pohoda.stock_parser import PohodaStockParser
        from app.integrations.pohoda.xml_builder import PohodaXMLBuilder
        from app.models.material_price import MaterialPrice

        results = {"synced": 0, "created": 0, "updated": 0, "errors": 0}

        async with AsyncSessionLocal() as session:
            try:
                # Build stock list request
                builder = PohodaXMLBuilder()
                request_xml = builder.build_stock_list_request()

                # Send to Pohoda (try to use client, graceful fallback)
                try:
                    from app.integrations.pohoda.client import PohodaClient

                    client = PohodaClient()
                    response_xml = await client.send(request_xml)
                except Exception as e:
                    logger.error("Pohoda client failed: %s", str(e))
                    return {"synced": 0, "created": 0, "updated": 0, "errors": 1, "error": str(e)}

                # Parse response
                parser = PohodaStockParser()
                stock_items = parser.parse_stock_list(response_xml)

                today = date.today()

                for item in stock_items:
                    try:
                        # Find existing material price by name
                        result = await session.execute(
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
                            session.add(new_price)
                            results["created"] += 1

                        results["synced"] += 1
                    except Exception as e:
                        logger.error("Failed to sync stock item %s: %s", item.code, str(e))
                        results["errors"] += 1

                await session.commit()

                logger.info(
                    "pohoda_inventory_sync_complete synced=%d created=%d updated=%d errors=%d",
                    results["synced"],
                    results["created"],
                    results["updated"],
                    results["errors"],
                )

                # Persisted notification via NotificationService
                try:
                    from app.models.notification import NotificationType
                    from app.models.user import UserRole
                    from app.services.notification import NotificationService

                    notif_service = NotificationService(session)
                    await notif_service.create_for_roles(
                        notification_type=NotificationType.POHODA_SYNC_COMPLETE,
                        title="Import skladových karet",
                        message=f"Synchronizováno {results['synced']} položek ({results['created']} nových, {results['updated']} aktualizovaných)",
                        roles=[UserRole.ADMIN, UserRole.UCETNI, UserRole.VEDENI],
                        link="/materialy",
                    )
                    await session.commit()
                except Exception:
                    logger.warning("inventory_sync_notification_failed")

                return results
            except Exception as e:
                await session.rollback()
                logger.error("pohoda_inventory_sync_failed error=%s", str(e))
                raise self.retry(exc=e) from e

    return _run_async(_sync())
