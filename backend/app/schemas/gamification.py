"""Gamification schemas."""

from pydantic import BaseModel


class PointsEntry(BaseModel):
    """Single points entry."""

    id: str
    action: str
    points: int
    description: str | None
    earned_at: str


class LeaderboardEntry(BaseModel):
    """Single leaderboard entry."""

    rank: int
    user_id: str
    user_name: str
    points_earned: int
    tasks_completed: int
    bonus_points: int
    total_points: int


class LeaderboardResponse(BaseModel):
    """Leaderboard API response."""

    period: str
    entries: list[LeaderboardEntry]
    total_users: int


class UserStatsResponse(BaseModel):
    """User gamification stats."""

    user_id: str
    user_name: str
    total_points: int
    rank: int
    orders_completed: int
    calculations_done: int
    documents_uploaded: int
    recent_points: list[PointsEntry]
