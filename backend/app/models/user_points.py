"""User points / gamification model."""

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPKMixin


class PointsPeriod(str, enum.Enum):
    """Period for points aggregation."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ALL_TIME = "all_time"


class PointsAction(str, enum.Enum):
    """Action that earned points."""

    ORDER_STATUS_CHANGE = "order_status_change"
    ORDER_CLAIM = "order_claim"
    CALCULATION_COMPLETE = "calculation_complete"
    DOCUMENT_UPLOAD = "document_upload"
    ORDER_COMPLETE = "order_complete"


class UserPoints(Base, UUIDPKMixin, TimestampMixin):
    """Tracks points earned by users."""

    __tablename__ = "user_points"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[PointsAction] = mapped_column(
        Enum(PointsAction, native_enum=False, length=50),
        nullable=False,
    )
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[UUID | None] = mapped_column(nullable=True)
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
