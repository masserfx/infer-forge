"""Subcontract model."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from .order import Order
    from .subcontractor import Subcontractor


class SubcontractStatus(str, enum.Enum):
    """Subcontract status enum."""

    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Subcontract(Base, UUIDPKMixin, TimestampMixin):
    """Subcontract (kooperace) - outsourced work for an order."""

    __tablename__ = "subcontracts"

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    subcontractor_id: Mapped[UUID] = mapped_column(
        ForeignKey("subcontractors.id"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="requested")
    planned_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    planned_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    actual_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="subcontracts")
    subcontractor: Mapped["Subcontractor"] = relationship("Subcontractor")

    __table_args__ = (
        Index("ix_subcontracts_order_id", "order_id"),
        Index("ix_subcontracts_subcontractor_id", "subcontractor_id"),
        Index("ix_subcontracts_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Subcontract(id={self.id}, order_id={self.order_id}, status={self.status})>"
