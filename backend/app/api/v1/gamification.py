"""Gamification API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models import PointsPeriod, User
from app.schemas.gamification import LeaderboardResponse, UserStatsResponse
from app.services.gamification import GamificationService

router = APIRouter(prefix="/gamifikace", tags=["Gamifikace"])


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    period: PointsPeriod = Query(
        default=PointsPeriod.ALL_TIME,
        description="Time period for leaderboard (daily, weekly, monthly, all_time)",
    ),
    skip: int = Query(default=0, ge=0, description="Number of entries to skip"),
    limit: int = Query(default=10, ge=1, le=100, description="Maximum entries to return"),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LeaderboardResponse:
    """Get leaderboard for a given period."""
    service = GamificationService(db)
    return await service.get_leaderboard(period=period, skip=skip, limit=limit)


@router.get("/me", response_model=UserStatsResponse)
async def get_my_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserStatsResponse:
    """Get current user's gamification stats.

    Args:
        user: Current authenticated user
        db: Database session

    Returns:
        User stats with points, rank, and action counts
    """
    service = GamificationService(db)
    return await service.get_user_stats(user_id=user.id)
