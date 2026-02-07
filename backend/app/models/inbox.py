"""InboxMessage model."""

import enum
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPKMixin


class InboxClassification(str, enum.Enum):
    """Inbox message classification enum."""

    POPTAVKA = "poptavka"
    OBJEDNAVKA = "objednavka"
    REKLAMACE = "reklamace"
    DOTAZ = "dotaz"
    PRILOHA = "priloha"


class InboxStatus(str, enum.Enum):
    """Inbox message status enum."""

    NEW = "new"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ESCALATED = "escalated"


class InboxMessage(Base, UUIDPKMixin, TimestampMixin):
    """Inbox message (email)."""

    __tablename__ = "inbox_messages"

    message_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    from_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    classification: Mapped[Optional[InboxClassification]] = mapped_column(
        Enum(InboxClassification, native_enum=False, length=20),
        nullable=True,
    )
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[InboxStatus] = mapped_column(
        Enum(InboxStatus, native_enum=False, length=20),
        nullable=False,
        default=InboxStatus.NEW,
        index=True,
    )
    customer_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    order_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    __table_args__ = (
        Index("ix_inbox_messages_status_received", "status", "received_at"),
        Index("ix_inbox_messages_classification", "classification"),
    )

    def __repr__(self) -> str:
        return f"<InboxMessage(id={self.id}, from_email='{self.from_email}', status={self.status.value})>"
