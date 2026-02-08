"""Offer model."""

import enum
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from .order import Order


class OfferStatus(str, enum.Enum):
    """Offer status enum."""

    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Offer(Base, UUIDPKMixin, TimestampMixin):
    """Offer (nabídka)."""

    __tablename__ = "offers"

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=False,
    )
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[OfferStatus] = mapped_column(
        Enum(OfferStatus, native_enum=False, length=20),
        nullable=False,
        default=OfferStatus.DRAFT,
    )
    pohoda_id: Mapped[int | None] = mapped_column(nullable=True)
    converted_to_order_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order",
        foreign_keys=[order_id],
        back_populates="offers",
    )
    converted_order: Mapped["Order | None"] = relationship(
        "Order",
        foreign_keys=[converted_to_order_id],
        uselist=False,
        viewonly=True,
    )

    __table_args__ = (
        Index("ix_offers_valid_until", "valid_until"),
        Index("ix_offers_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Offer(id={self.id}, number='{self.number}', status={self.status.value})>"
