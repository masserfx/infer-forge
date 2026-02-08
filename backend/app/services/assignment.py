"""Smart order assignment service."""

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderStatus
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


class AssignmentService:
    """Suggests best assignee for an order based on workload and history."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def suggest_assignee(self, order_id: UUID) -> dict[str, str | list[dict[str, str | int]] | dict[str, str | int] | None]:
        """Suggest the best assignee for an order.

        Criteria:
        1. Current workload (fewer active orders = better)
        2. Role compatibility (technolog/obchodnik preferred)
        """
        # Get eligible users
        result = await self.db.execute(
            select(User).where(
                User.is_active,
                User.role.in_([UserRole.TECHNOLOG, UserRole.OBCHODNIK, UserRole.VEDENI]),
            )
        )
        users = list(result.scalars().all())

        if not users:
            return {"suggestion": None, "reason": "Žádní dostupní uživatelé"}

        # Get workload per user
        scored_users = []
        for u in users:
            workload_result = await self.db.execute(
                select(func.count()).select_from(Order).where(
                    Order.assigned_to == u.id,
                    Order.status.notin_([OrderStatus.DOKONCENO]),
                )
            )
            active_count = workload_result.scalar() or 0

            # Score: lower workload = higher score
            score = 100 - (active_count * 10)

            # Bonus for technolog role
            if u.role == UserRole.TECHNOLOG:
                score += 5

            scored_users.append({
                "user_id": str(u.id),
                "user_name": u.full_name,
                "role": u.role.value,
                "active_orders": active_count,
                "score": score,
            })

        # Sort by score (highest first)
        scored_users.sort(key=lambda x: x["score"], reverse=True)
        best = scored_users[0]

        return {
            "suggestion": {
                "user_id": best["user_id"],
                "user_name": best["user_name"],
                "role": best["role"],
                "active_orders": best["active_orders"],
                "reason": f"Nejméně aktivních zakázek ({best['active_orders']})",
            },
            "alternatives": scored_users[1:3],
        }
