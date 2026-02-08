"""ProcessingTask model for orchestration audit trail."""

import enum
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPKMixin


class ProcessingStage(str, enum.Enum):
    INGEST = "ingest"
    CLASSIFY = "classify"
    PARSE = "parse"
    OCR = "ocr"
    ANALYZE = "analyze"
    ORCHESTRATE = "orchestrate"
    CALCULATE = "calculate"
    OFFER = "offer"


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    DLQ = "dlq"


class ProcessingTask(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "processing_tasks"

    inbox_message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("inbox_messages.id", ondelete="SET NULL"), nullable=True, index=True
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    stage: Mapped[ProcessingStage] = mapped_column(
        Enum(ProcessingStage, native_enum=False, length=20), nullable=False
    )
    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, native_enum=False, length=20),
        nullable=False, default=ProcessingStatus.PENDING
    )
    input_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_processing_tasks_stage_status", "stage", "status"),
        Index("ix_processing_tasks_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ProcessingTask(id={self.id}, stage={self.stage.value}, status={self.status.value})>"
