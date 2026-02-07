"""AuditLog model."""

import enum
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDPKMixin


class AuditAction(str, enum.Enum):
    """Audit action enum."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class AuditLog(Base, UUIDPKMixin):
    """Audit log (ISO 9001 compliance)."""

    __tablename__ = "audit_logs"

    user_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, native_enum=False, length=20),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_timestamp", "timestamp"),
        Index("ix_audit_logs_user_timestamp", "user_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action.value}, entity_type='{self.entity_type}')>"
