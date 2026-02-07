"""Customer model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from .order import Order


class Customer(Base, UUIDPKMixin, TimestampMixin):
    """Customer (zákazník)."""

    __tablename__ = "customers"

    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ico: Mapped[str] = mapped_column(String(8), unique=True, nullable=False, index=True)
    dic: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    pohoda_id: Mapped[int | None] = mapped_column(nullable=True)
    pohoda_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_customers_company_name", "company_name"),
        Index("ix_customers_email", "email"),
    )

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, company_name='{self.company_name}', ico='{self.ico}')>"
