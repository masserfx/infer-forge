"""DeadLetterQueue model for failed task handling."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPKMixin


class DeadLetterEntry(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "dead_letter_queue"

    original_task: Mapped[str] = mapped_column(String(255), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_traceback: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[UUID | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("ix_dead_letter_queue_resolved", "resolved"),
        Index("ix_dead_letter_queue_stage", "stage"),
    )

    def __repr__(self) -> str:
        return f"<DeadLetterEntry(id={self.id}, stage='{self.stage}', resolved={self.resolved})>"
