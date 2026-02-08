"""Dashboard recommendation service."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Calculation,
    CalculationStatus,
    InboxMessage,
    InboxStatus,
    Offer,
    Order,
    OrderStatus,
)

logger = logging.getLogger(__name__)


class RecommendationService:
    """Analyzes system state and generates prioritized action recommendations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_recommendations(self, limit: int = 5) -> list[dict[str, str]]:
        """Get prioritized recommendations for dashboard.

        Returns max `limit` items sorted by severity (critical > warning > info).
        """
        recommendations = []

        # 1. Orders past due date
        overdue = await self._get_overdue_orders()
        recommendations.extend(overdue)

        # 2. Unapproved calculations older than 3 days
        old_calcs = await self._get_old_draft_calculations()
        recommendations.extend(old_calcs)

        # 3. Unassigned orders
        unassigned = await self._get_unassigned_orders()
        recommendations.extend(unassigned)

        # 4. Inbox messages waiting > 24h
        waiting_inbox = await self._get_waiting_inbox()
        recommendations.extend(waiting_inbox)

        # 5. Approved calculations without offer
        no_offer = await self._get_calculations_without_offer()
        recommendations.extend(no_offer)

        # Sort by severity priority: critical=0, warning=1, info=2
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        recommendations.sort(key=lambda r: severity_order.get(r["severity"], 3))

        return recommendations[:limit]

    async def _get_overdue_orders(self) -> list[dict[str, str]]:
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(Order)
            .where(
                Order.due_date < now,
                Order.status.notin_([OrderStatus.DOKONCENO]),
            )
            .options(selectinload(Order.customer))
            .order_by(Order.due_date.asc())
            .limit(5)
        )
        orders = result.scalars().all()
        return [
            {
                "type": "overdue_order",
                "severity": "critical",
                "title": f"Zakázka {o.number} po termínu",
                "description": f"Termín: {o.due_date.strftime('%d.%m.%Y') if o.due_date else 'N/A'}, stav: {o.status.value}",
                "action_url": f"/zakazky/{o.id}",
                "entity_id": str(o.id),
            }
            for o in orders
        ]

    async def _get_old_draft_calculations(self) -> list[dict[str, str]]:
        threshold = datetime.now(UTC) - timedelta(days=3)
        result = await self.db.execute(
            select(Calculation)
            .where(
                Calculation.status == CalculationStatus.DRAFT,
                Calculation.created_at < threshold,
            )
            .order_by(Calculation.created_at.asc())
            .limit(5)
        )
        calcs = result.scalars().all()
        return [
            {
                "type": "old_draft_calculation",
                "severity": "warning",
                "title": f"Neschválená kalkulace: {c.name}",
                "description": f"Vytvořena {c.created_at.strftime('%d.%m.%Y')}, čeká na schválení",
                "action_url": f"/kalkulace/{c.id}",
                "entity_id": str(c.id),
            }
            for c in calcs
        ]

    async def _get_unassigned_orders(self) -> list[dict[str, str]]:
        result = await self.db.execute(
            select(Order)
            .where(
                Order.assigned_to.is_(None),
                Order.status.notin_([OrderStatus.DOKONCENO]),
            )
            .options(selectinload(Order.customer))
            .order_by(Order.created_at.desc())
            .limit(5)
        )
        orders = result.scalars().all()
        return [
            {
                "type": "unassigned_order",
                "severity": "warning",
                "title": f"Nepřiřazená zakázka {o.number}",
                "description": f"Stav: {o.status.value}, priorita: {o.priority.value}",
                "action_url": f"/zakazky/{o.id}",
                "entity_id": str(o.id),
            }
            for o in orders
        ]

    async def _get_waiting_inbox(self) -> list[dict[str, str]]:
        threshold = datetime.now(UTC) - timedelta(hours=24)
        result = await self.db.execute(
            select(InboxMessage)
            .where(
                InboxMessage.status == InboxStatus.NEW,
                InboxMessage.created_at < threshold,
            )
            .order_by(InboxMessage.created_at.asc())
            .limit(5)
        )
        messages = result.scalars().all()
        return [
            {
                "type": "waiting_inbox",
                "severity": "warning",
                "title": f"Nezpracovaný email: {m.subject[:50]}",
                "description": f"Od: {m.from_email}, přijato: {m.received_at.strftime('%d.%m.%Y %H:%M') if m.received_at else 'N/A'}",
                "action_url": "/inbox",
                "entity_id": str(m.id),
            }
            for m in messages
        ]

    async def _get_calculations_without_offer(self) -> list[dict[str, str]]:
        # Find approved calculations that don't have an associated offer
        result = await self.db.execute(
            select(Calculation)
            .where(Calculation.status == CalculationStatus.APPROVED)
            .order_by(Calculation.updated_at.desc())
            .limit(10)
        )
        calcs = list(result.scalars().all())

        # Check which ones have offers
        recs = []
        for c in calcs:
            offer_result = await self.db.execute(
                select(func.count()).select_from(Offer).where(Offer.order_id == c.order_id)
            )
            offer_count = offer_result.scalar() or 0
            if offer_count == 0:
                recs.append({
                    "type": "approved_without_offer",
                    "severity": "info",
                    "title": f"Schválená kalkulace bez nabídky: {c.name}",
                    "description": "Kalkulace schválena, ale nabídka zatím nebyla vytvořena",
                    "action_url": f"/kalkulace/{c.id}",
                    "entity_id": str(c.id),
                })
        return recs[:5]
