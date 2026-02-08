"""Order and OrderItem models."""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from .calculation import Calculation
    from .customer import Customer
    from .offer import Offer
    from .operation import Operation
    from .order_embedding import OrderEmbedding
    from .subcontract import Subcontract


class OrderStatus(str, enum.Enum):
    """Order status enum."""

    POPTAVKA = "poptavka"
    NABIDKA = "nabidka"
    OBJEDNAVKA = "objednavka"
    VYROBA = "vyroba"
    EXPEDICE = "expedice"
    FAKTURACE = "fakturace"
    DOKONCENO = "dokonceno"


class OrderPriority(str, enum.Enum):
    """Order priority enum."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Order(Base, UUIDPKMixin, TimestampMixin):
    """Order (zakázka)."""

    __tablename__ = "orders"

    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False, length=20),
        nullable=False,
        index=True,
    )
    priority: Mapped[OrderPriority] = mapped_column(
        Enum(OrderPriority, native_enum=False, length=20),
        nullable=False,
        default=OrderPriority.NORMAL,
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(nullable=True)
    pohoda_id: Mapped[int | None] = mapped_column(nullable=True)
    pohoda_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    source_offer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("offers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    offers: Mapped[list["Offer"]] = relationship(
        "Offer",
        foreign_keys="[Offer.order_id]",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    calculations: Mapped[list["Calculation"]] = relationship(
        "Calculation",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    embedding: Mapped["OrderEmbedding | None"] = relationship(
        "OrderEmbedding",
        back_populates="order",
        uselist=False,
        cascade="all, delete-orphan",
    )
    source_offer: Mapped["Offer | None"] = relationship(
        "Offer",
        foreign_keys=[source_offer_id],
        uselist=False,
        viewonly=True,
    )
    operations: Mapped[list["Operation"]] = relationship(
        "Operation",
        back_populates="order",
        order_by="Operation.sequence",
        cascade="all, delete-orphan",
    )
    subcontracts: Mapped[list["Subcontract"]] = relationship(
        "Subcontract",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_orders_status_priority", "status", "priority"),
        Index("ix_orders_due_date", "due_date"),
    )

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, number='{self.number}', status={self.status.value})>"


class OrderItem(Base, UUIDPKMixin):
    """Order item (položka zakázky)."""

    __tablename__ = "order_items"

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    material: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
    )
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="ks")
    dn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    drawing_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")

    def __repr__(self) -> str:
        return f"<OrderItem(id={self.id}, name='{self.name}', quantity={self.quantity})>"
