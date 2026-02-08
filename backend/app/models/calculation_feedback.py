"""Calculation feedback model for AI learning loop."""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CorrectionType(str, enum.Enum):
    PRICE = "price"
    QUANTITY = "quantity"
    ADDED = "added"
    REMOVED = "removed"
    MARGIN = "margin"


class CalculationFeedback(Base):
    __tablename__ = "calculation_feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    calculation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("calculations.id", ondelete="CASCADE"), nullable=False
    )
    original_items: Mapped[str | None] = mapped_column(type_=Text, nullable=True)
    corrected_items: Mapped[str | None] = mapped_column(type_=Text, nullable=True)
    correction_type: Mapped[CorrectionType] = mapped_column(
        Enum(CorrectionType, native_enum=False), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
