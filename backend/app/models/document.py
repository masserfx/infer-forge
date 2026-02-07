"""Document model for file management."""

import enum
from uuid import UUID

from sqlalchemy import BigInteger, Enum, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

from .base import TimestampMixin, UUIDPKMixin


class DocumentCategory(str, enum.Enum):
    """Document category for ISO 9001 classification."""

    VYKRES = "vykres"  # Technical drawing
    ATESTACE = "atestace"  # Material certificate EN 10-204
    WPS = "wps"  # Welding Procedure Specification
    PRUVODKA = "pruvodka"  # Manufacturing route card
    FAKTURA = "faktura"  # Invoice
    NABIDKA = "nabidka"  # Offer/quotation
    OBJEDNAVKA = "objednavka"  # Purchase order
    PROTOKOL = "protokol"  # NDT/test protocol
    OSTATNI = "ostatni"  # Other


class Document(Base, UUIDPKMixin, TimestampMixin):
    """Document attached to an entity (order, customer, offer)."""

    __tablename__ = "documents"

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    category: Mapped[DocumentCategory] = mapped_column(
        Enum(DocumentCategory, native_enum=False, length=20),
        nullable=False,
        default=DocumentCategory.OSTATNI,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[UUID | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("ix_documents_entity", "entity_type", "entity_id"),
        Index("ix_documents_category", "category"),
    )

    def __repr__(self) -> str:
        return (
            f"<Document(id={self.id}, file_name='{self.file_name}', "
            f"category='{self.category}', entity_type='{self.entity_type}')>"
        )
