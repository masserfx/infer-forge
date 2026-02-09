"""Celery tasks for deadline monitoring."""

import asyncio
import logging

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(name="app.services.deadline_tasks.check_operation_deadlines")
def check_operation_deadlines() -> dict:  # type: ignore[no-untyped-def]
    """Check production operation deadlines and send alerts.

    Runs periodically via Celery Beat (3x daily: 7:00, 11:00, 15:00).

    Returns:
        Dict with alert count.
    """
    logger.info("check_operation_deadlines.started")

    async def _run_check() -> list[dict]:
        from app.core.config import get_settings
        from app.services.deadline_monitor import DeadlineMonitorService

        settings = get_settings()
        async with AsyncSessionLocal() as session:
            try:
                service = DeadlineMonitorService(
                    db=session,
                    api_key=settings.ANTHROPIC_API_KEY or None,
                )
                alerts = await service.check_deadlines()
                await session.commit()
                return alerts
            except Exception:
                await session.rollback()
                raise

    try:
        alerts = asyncio.run(_run_check())
        logger.info("check_operation_deadlines.completed alerts=%d", len(alerts))
        return {"status": "completed", "alert_count": len(alerts)}
    except Exception:
        logger.exception("check_operation_deadlines.failed")
        return {"status": "failed", "alert_count": 0}
