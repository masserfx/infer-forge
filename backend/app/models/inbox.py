"""InboxMessage model."""

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPKMixin


class MessageDirection(str, enum.Enum):
    """Email direction enum."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"


class InboxClassification(str, enum.Enum):
    """Inbox message classification enum."""

    POPTAVKA = "poptavka"
    OBJEDNAVKA = "objednavka"
    REKLAMACE = "reklamace"
    DOTAZ = "dotaz"
    PRILOHA = "priloha"
    INFORMACE_ZAKAZKA = "informace_zakazka"
    FAKTURA = "faktura"
    OBCHODNI_SDELENI = "obchodni_sdeleni"


class InboxStatus(str, enum.Enum):
    """Inbox message status enum."""

    NEW = "new"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ESCALATED = "escalated"
    CLASSIFIED = "classified"
    REVIEW = "review"
    ARCHIVED = "archived"


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
    classification: Mapped[InboxClassification | None] = mapped_column(
        Enum(InboxClassification, native_enum=False, length=30),
        nullable=True,
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[InboxStatus] = mapped_column(
        Enum(InboxStatus, native_enum=False, length=20),
        nullable=False,
        default=InboxStatus.NEW,
        index=True,
    )
    customer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    order_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    auto_reply_sent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    direction: Mapped[MessageDirection] = mapped_column(
        Enum(MessageDirection, native_enum=False, length=10),
        nullable=False,
        default=MessageDirection.INBOUND,
        server_default="INBOUND",
    )

    # Orchestration fields
    parsed_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    references_header: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processing_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    needs_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # Relationships
    attachments = relationship("EmailAttachment", backref="inbox_message", lazy="selectin")

    __table_args__ = (
        Index("ix_inbox_messages_status_received", "status", "received_at"),
        Index("ix_inbox_messages_classification", "classification"),
        Index("ix_inbox_messages_thread_id", "thread_id"),
        Index("ix_inbox_messages_from_email_received_at", "from_email", "received_at"),
    )

    def __repr__(self) -> str:
        return f"<InboxMessage(id={self.id}, from_email='{self.from_email}', status={self.status.value})>"
