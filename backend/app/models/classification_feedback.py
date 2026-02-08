"""Classification feedback model for email classifier learning."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ClassificationFeedback(Base):
    """Stores user corrections to email classifications.

    When users reclassify an email, the original and corrected
    categories are stored for improving the heuristic classifier.
    """

    __tablename__ = "classification_feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    inbox_message_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("inbox_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_category: Mapped[str] = mapped_column(String(50), nullable=False)
    corrected_category: Mapped[str] = mapped_column(String(50), nullable=False)
    subject_preview: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
