"""DrawingAnalysis model for persisting drawing analysis results."""

from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPKMixin


class DrawingAnalysis(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "drawing_analyses"

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    dimensions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    materials: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tolerances: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    surface_treatments: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    welding_requirements: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_drawing_analyses_document_id", "document_id"),
    )

    def __repr__(self) -> str:
        return f"<DrawingAnalysis(id={self.id}, document_id={self.document_id})>"
