"""Calculation models for cost estimation."""

import enum
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from .order import Order


class CostType(str, enum.Enum):
    """Type of cost in calculation."""

    MATERIAL = "material"  # Material costs (steel, fittings, etc.)
    LABOR = "labor"  # Labor costs (welding, machining, assembly)
    COOPERATION = "cooperation"  # Subcontracted work (NDT, coating, transport)
    OVERHEAD = "overhead"  # Overhead costs (manufacturing, administrative)


class CalculationStatus(str, enum.Enum):
    """Calculation lifecycle status."""

    DRAFT = "draft"
    APPROVED = "approved"
    OFFERED = "offered"  # Offer generated from this calculation


class Calculation(Base, UUIDPKMixin, TimestampMixin):
    """Calculation (kalkulace) for an order."""

    __tablename__ = "calculations"

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[CalculationStatus] = mapped_column(
        Enum(CalculationStatus, native_enum=False, length=20),
        nullable=False,
        default=CalculationStatus.DRAFT,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(nullable=True)

    # Aggregated totals (recalculated from items)
    material_total: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2), nullable=False, default=Decimal("0")
    )
    labor_total: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2), nullable=False, default=Decimal("0")
    )
    cooperation_total: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2), nullable=False, default=Decimal("0")
    )
    overhead_total: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2), nullable=False, default=Decimal("0")
    )
    margin_percent: Mapped[Decimal] = mapped_column(
        Numeric(precision=5, scale=2), nullable=False, default=Decimal("15")
    )
    margin_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2), nullable=False, default=Decimal("0")
    )
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2), nullable=False, default=Decimal("0")
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="calculations")
    items: Mapped[list["CalculationItem"]] = relationship(
        "CalculationItem",
        back_populates="calculation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("ix_calculations_status", "status"),)

    def __repr__(self) -> str:
        return (
            f"<Calculation(id={self.id}, name='{self.name}', " f"total_price={self.total_price})>"
        )


class CalculationItem(Base, UUIDPKMixin):
    """Single cost line item in a calculation."""

    __tablename__ = "calculation_items"

    calculation_id: Mapped[UUID] = mapped_column(
        ForeignKey("calculations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cost_type: Mapped[CostType] = mapped_column(
        Enum(CostType, native_enum=False, length=20),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=3), nullable=False, default=Decimal("1")
    )
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="ks")
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2), nullable=False, default=Decimal("0")
    )
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2), nullable=False, default=Decimal("0")
    )

    # Relationships
    calculation: Mapped["Calculation"] = relationship("Calculation", back_populates="items")

    __table_args__ = (Index("ix_calculation_items_cost_type", "cost_type"),)

    def __repr__(self) -> str:
        return (
            f"<CalculationItem(id={self.id}, name='{self.name}', "
            f"cost_type={self.cost_type.value}, total={self.total_price})>"
        )
