"""Operation model for production planning."""

import enum
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPKMixin


class OperationStatus(str, enum.Enum):
    """Operation status enum."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Operation(Base, UUIDPKMixin, TimestampMixin):
    """Production operation on an order.

    Represents a single step in the production process with scheduling
    and tracking information. Operations are sequenced and tracked through
    their lifecycle from planning to completion.

    Attributes:
        order_id: Foreign key to Order (zakázka)
        name: Operation name (e.g., "Řezání", "Svařování", "NDT")
        description: Detailed description of the operation
        sequence: Order sequence number (1, 2, 3...)
        duration_hours: Estimated duration in hours
        responsible: Name of responsible person/team
        planned_start: Planned start datetime
        planned_end: Planned end datetime
        actual_start: Actual start datetime
        actual_end: Actual end datetime
        status: Current operation status
        notes: Additional notes
    """

    __tablename__ = "operations"

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sequence: Mapped[int] = mapped_column(nullable=False)
    duration_hours: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=8, scale=2),
        nullable=True,
    )
    responsible: Mapped[str | None] = mapped_column(String(255), nullable=True)
    planned_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    planned_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    actual_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    actual_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        SAEnum(OperationStatus, native_enum=False, length=20),
        nullable=False,
        default=OperationStatus.PLANNED,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="operations")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_operations_order_id_sequence", "order_id", "sequence"),
        Index("ix_operations_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Operation(id={self.id}, name='{self.name}', sequence={self.sequence}, status={self.status})>"
