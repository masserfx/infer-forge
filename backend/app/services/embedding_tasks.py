"""Celery tasks for embedding generation."""

import asyncio
import logging

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def generate_order_embedding(self, order_id: str) -> dict:  # type: ignore[no-untyped-def]
    """Generate embedding for an order as background task.

    Args:
        order_id: Order UUID string.

    Returns:
        Dict with result status.
    """
    logger.info("generate_order_embedding.started order_id=%s", order_id)

    async def _generate() -> dict:
        from uuid import UUID

        from app.services.embedding import EmbeddingService

        async with AsyncSessionLocal() as session:
            service = EmbeddingService(session)
            try:
                result = await service.generate_embedding(UUID(order_id))
                await session.commit()

                if result:
                    logger.info("generate_order_embedding.completed order_id=%s", order_id)
                    return {"status": "completed", "order_id": order_id}
                else:
                    logger.warning(
                        "generate_order_embedding.order_not_found order_id=%s", order_id
                    )
                    return {"status": "not_found", "order_id": order_id}
            except Exception as e:
                await session.rollback()
                raise e

    try:
        return asyncio.run(_generate())
    except Exception as exc:
        logger.exception("generate_order_embedding.failed order_id=%s", order_id)
        raise self.retry(exc=exc) from exc
