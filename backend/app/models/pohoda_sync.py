"""PohodaSyncLog model for tracking Pohoda XML synchronization."""

import enum
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Enum, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDPKMixin


class SyncDirection(str, enum.Enum):
    """Sync direction enum."""

    EXPORT = "export"  # INFER FORGE -> Pohoda
    IMPORT = "import"  # Pohoda -> INFER FORGE


class SyncStatus(str, enum.Enum):
    """Sync status enum."""

    PENDING = "pending"
    SUCCESS = "success"
    ERROR = "error"


class PohodaSyncLog(Base, UUIDPKMixin):
    """Pohoda synchronization log entry.

    Tracks every XML exchange with Pohoda mServer for audit/debugging.
    """

    __tablename__ = "pohoda_sync_logs"

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    direction: Mapped[SyncDirection] = mapped_column(
        Enum(SyncDirection, native_enum=False, length=10),
        nullable=False,
    )
    pohoda_doc_number: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
    )
    xml_request: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    xml_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, native_enum=False, length=10),
        nullable=False,
        default=SyncStatus.PENDING,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_pohoda_sync_logs_entity", "entity_type", "entity_id"),
        Index("ix_pohoda_sync_logs_status", "status"),
        Index("ix_pohoda_sync_logs_synced_at", "synced_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<PohodaSyncLog(id={self.id}, entity_type='{self.entity_type}', "
            f"direction={self.direction.value}, status={self.status.value})>"
        )
