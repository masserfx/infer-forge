"""Predictive due date estimation based on historical data."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderStatus

logger = logging.getLogger(__name__)


class PredictionService:
    """Predicts order completion time based on historical data."""

    MIN_TRAINING_SAMPLES = 5

    def __init__(self, db: AsyncSession):
        self.db = db

    async def predict_due_date(self, order_id: UUID) -> dict[str, int | float | str]:
        """Predict realistic completion time for an order.

        Uses historical data to estimate days needed. Falls back to
        simple average if insufficient training data.
        """
        # Load the order
        result = await self.db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            return {"error": "Order not found"}

        # Get completed orders for training
        completed = await self.db.execute(
            select(Order)
            .where(Order.status == OrderStatus.DOKONCENO)
            .order_by(Order.updated_at.desc())
            .limit(100)
        )
        completed_orders = list(completed.scalars().all())

        if len(completed_orders) < self.MIN_TRAINING_SAMPLES:
            return {
                "predicted_days": 14,
                "confidence": 0.3,
                "method": "default",
                "message": "Nedostatek historických dat, použit výchozí odhad 14 dní",
            }

        # Calculate actual completion times
        durations = []
        for o in completed_orders:
            if o.created_at and o.updated_at:
                days = (o.updated_at - o.created_at).days
                if days > 0:
                    durations.append(days)

        if not durations:
            return {
                "predicted_days": 14,
                "confidence": 0.3,
                "method": "default",
                "message": "Nelze určit doby dokončení z historických dat",
            }

        # Simple statistical prediction
        sorted_d = sorted(durations)
        median_days = sorted_d[len(sorted_d) // 2]

        # Use items count as complexity factor
        items_count = len(order.items) if hasattr(order, 'items') and order.items else 1
        complexity_factor = min(items_count / 3.0, 2.0)  # cap at 2x

        predicted = int(median_days * max(complexity_factor, 0.5))
        low = max(int(predicted * 0.7), 1)
        high = int(predicted * 1.4)

        confidence = min(0.5 + len(durations) / 200.0, 0.9)

        return {
            "predicted_days": predicted,
            "predicted_range_low": low,
            "predicted_range_high": high,
            "confidence": round(confidence, 2),
            "method": "historical_median",
            "sample_size": len(durations),
            "message": f"Odhad: {low}-{high} dní ({int(confidence * 100)}% spolehlivost)",
        }
