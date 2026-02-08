"""EmailAttachment model for storing email attachment metadata."""

import enum
from uuid import UUID

from sqlalchemy import BigInteger, Enum, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPKMixin


class OCRStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    SKIPPED = "skipped"


class EmailAttachment(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "email_attachments"

    inbox_message_id: Mapped[UUID] = mapped_column(
        ForeignKey("inbox_messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ocr_status: Mapped[OCRStatus] = mapped_column(
        Enum(OCRStatus, native_enum=False, length=20),
        nullable=False, default=OCRStatus.PENDING
    )
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    detected_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_email_attachments_ocr_status", "ocr_status"),
    )

    def __repr__(self) -> str:
        return f"<EmailAttachment(id={self.id}, filename='{self.filename}', ocr_status={self.ocr_status.value})>"
