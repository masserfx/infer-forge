"""Subcontractor model."""

from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPKMixin


class Subcontractor(Base, UUIDPKMixin, TimestampMixin):
    """Subcontractor (subdodavatel) for outsourced work."""

    __tablename__ = "subcontractors"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ico: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    specialization: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="e.g. svařování, NDT, povrchová úprava",
    )
    rating: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Rating 1-5",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_subcontractors_name", "name"),
        Index("ix_subcontractors_is_active", "is_active"),
        Index("ix_subcontractors_specialization", "specialization"),
    )

    def __repr__(self) -> str:
        return f"<Subcontractor(id={self.id}, name='{self.name}', active={self.is_active})>"
