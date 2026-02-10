"""Gamification service for awarding and tracking user points."""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OrderStatus, PointsAction, PointsPeriod, User, UserPoints
from app.schemas.gamification import (
    LeaderboardEntry,
    LeaderboardResponse,
    PointsEntry,
    UserStatsResponse,
)

logger = logging.getLogger(__name__)

# Points awarded for order status transitions
POINTS_INQUIRY_TO_OFFER = 5
POINTS_OFFER_TO_ORDER = 10
POINTS_ORDER_TO_PRODUCTION = 5
POINTS_PRODUCTION_TO_SHIPPING = 10
POINTS_SHIPPING_TO_INVOICING = 5
POINTS_INVOICING_TO_COMPLETED = 20


class GamificationService:
    """Service for managing user points and gamification."""

    def __init__(self, db: AsyncSession):
        """Initialize service.

        Args:
            db: Async database session
        """
        self.db = db

    async def award_points(
        self,
        user_id: UUID,
        action: PointsAction,
        points: int,
        description: str | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
    ) -> UserPoints:
        """Award points to a user.

        Args:
            user_id: User UUID
            action: Action that earned points
            points: Points to award
            description: Optional description
            entity_type: Optional entity type (order, calculation, document)
            entity_id: Optional entity UUID

        Returns:
            Created UserPoints record
        """
        user_points = UserPoints(
            user_id=user_id,
            action=action,
            points=points,
            description=description,
            entity_type=entity_type,
            entity_id=entity_id,
            earned_at=datetime.now(UTC),
        )
        self.db.add(user_points)
        await self.db.flush()
        await self.db.refresh(user_points)

        logger.info(
            "Awarded %d points to user %s for action %s",
            points,
            str(user_id),
            action.value,
        )
        return user_points

    def _get_period_start(self, period: PointsPeriod) -> datetime | None:
        """Get start datetime for a period.

        Args:
            period: Points period

        Returns:
            Start datetime or None for all_time
        """
        now = datetime.now(UTC)

        if period == PointsPeriod.DAILY:
            return datetime(now.year, now.month, now.day, tzinfo=UTC)
        elif period == PointsPeriod.WEEKLY:
            # Start of week (Monday)
            days_since_monday = now.weekday()
            monday = now - timedelta(days=days_since_monday)
            return datetime(monday.year, monday.month, monday.day, tzinfo=UTC)
        elif period == PointsPeriod.MONTHLY:
            return datetime(now.year, now.month, 1, tzinfo=UTC)
        else:  # ALL_TIME
            return None

    async def get_leaderboard(
        self, period: PointsPeriod = PointsPeriod.ALL_TIME, skip: int = 0, limit: int = 10
    ) -> LeaderboardResponse:
        """Get leaderboard for a period.

        Args:
            period: Time period for aggregation
            skip: Number of entries to skip
            limit: Maximum number of entries to return

        Returns:
            Leaderboard with ranked entries
        """
        period_start = self._get_period_start(period)

        # Build query
        query = (
            select(
                UserPoints.user_id,
                func.sum(UserPoints.points).label("total_points"),
                func.count(UserPoints.id).label("tasks_completed"),
            )
            .group_by(UserPoints.user_id)
            .order_by(func.sum(UserPoints.points).desc())
        )

        # Apply period filter
        if period_start:
            query = query.where(UserPoints.earned_at >= period_start)

        # Execute query
        result = await self.db.execute(query.offset(skip).limit(limit))
        rows = result.all()

        # Batch-load user details (avoid N+1)
        user_ids = [row.user_id for row in rows]
        if user_ids:
            users_result = await self.db.execute(
                select(User).where(User.id.in_(user_ids))
            )
            users_map = {u.id: u for u in users_result.scalars().all()}
        else:
            users_map = {}

        entries = []
        for rank, row in enumerate(rows, start=skip + 1):
            user_id = row.user_id
            total_points = row.total_points or 0
            tasks_completed = row.tasks_completed or 0

            user = users_map.get(user_id)
            if user:
                bonus_points = 0
                points_earned = total_points - bonus_points

                entries.append(
                    LeaderboardEntry(
                        rank=rank,
                        user_id=str(user_id),
                        user_name=user.full_name,
                        points_earned=points_earned,
                        tasks_completed=tasks_completed,
                        bonus_points=bonus_points,
                        total_points=total_points,
                    )
                )

        return LeaderboardResponse(
            period=period.value, entries=entries, total_users=len(entries)
        )

    async def get_user_stats(self, user_id: UUID) -> UserStatsResponse:
        """Get gamification stats for a user.

        Args:
            user_id: User UUID

        Returns:
            User stats with total points, rank, action counts
        """
        # Get total points
        total_query = select(func.sum(UserPoints.points)).where(
            UserPoints.user_id == user_id
        )
        result = await self.db.execute(total_query)
        total_points = result.scalar() or 0

        # Get rank (count users with more points)
        rank_query = (
            select(func.count(func.distinct(UserPoints.user_id)))
            .select_from(UserPoints)
            .where(
                UserPoints.user_id.in_(
                    select(UserPoints.user_id)
                    .group_by(UserPoints.user_id)
                    .having(func.sum(UserPoints.points) > total_points)
                )
            )
        )
        result = await self.db.execute(rank_query)
        rank = (result.scalar() or 0) + 1

        # Get action counts
        orders_query = select(func.count(UserPoints.id)).where(
            UserPoints.user_id == user_id,
            UserPoints.action == PointsAction.ORDER_COMPLETE,
        )
        result = await self.db.execute(orders_query)
        orders_completed = result.scalar() or 0

        calcs_query = select(func.count(UserPoints.id)).where(
            UserPoints.user_id == user_id,
            UserPoints.action == PointsAction.CALCULATION_COMPLETE,
        )
        result = await self.db.execute(calcs_query)
        calculations_done = result.scalar() or 0

        docs_query = select(func.count(UserPoints.id)).where(
            UserPoints.user_id == user_id,
            UserPoints.action == PointsAction.DOCUMENT_UPLOAD,
        )
        result = await self.db.execute(docs_query)
        documents_uploaded = result.scalar() or 0

        # Get recent points (last 10)
        recent_query = (
            select(UserPoints)
            .where(UserPoints.user_id == user_id)
            .order_by(UserPoints.earned_at.desc())
            .limit(10)
        )
        result = await self.db.execute(recent_query)
        recent_records = result.scalars().all()

        recent_points = [
            PointsEntry(
                id=str(record.id),
                action=record.action.value,
                points=record.points,
                description=record.description,
                earned_at=record.earned_at.isoformat(),
            )
            for record in recent_records
        ]

        # Get user details
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one()

        return UserStatsResponse(
            user_id=str(user_id),
            user_name=user.full_name,
            total_points=int(total_points),
            rank=rank,
            orders_completed=orders_completed,
            calculations_done=calculations_done,
            documents_uploaded=documents_uploaded,
            recent_points=recent_points,
        )

    def calculate_order_points(
        self, old_status: OrderStatus, new_status: OrderStatus
    ) -> int:
        """Calculate points for order status transition.

        Args:
            old_status: Previous order status
            new_status: New order status

        Returns:
            Points to award (0 if no points for this transition)
        """
        # Points mapping for transitions
        transitions = {
            (OrderStatus.POPTAVKA, OrderStatus.NABIDKA): POINTS_INQUIRY_TO_OFFER,
            (OrderStatus.NABIDKA, OrderStatus.OBJEDNAVKA): POINTS_OFFER_TO_ORDER,
            (OrderStatus.OBJEDNAVKA, OrderStatus.VYROBA): POINTS_ORDER_TO_PRODUCTION,
            (OrderStatus.VYROBA, OrderStatus.EXPEDICE): POINTS_PRODUCTION_TO_SHIPPING,
            (OrderStatus.EXPEDICE, OrderStatus.FAKTURACE): POINTS_SHIPPING_TO_INVOICING,
            (OrderStatus.FAKTURACE, OrderStatus.DOKONCENO): POINTS_INVOICING_TO_COMPLETED,
        }

        return transitions.get((old_status, new_status), 0)
