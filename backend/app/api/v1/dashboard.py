"""Dashboard API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.user import User, UserRole
from app.services.recommendation import RecommendationService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/recommendations")
async def get_recommendations(
    limit: int = Query(default=5, ge=1, le=10),
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI, UserRole.UCETNI)),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, str]]:
    """Get AI-analyzed recommendations for dashboard actions."""
    service = RecommendationService(db)
    return await service.get_recommendations(limit=limit)
