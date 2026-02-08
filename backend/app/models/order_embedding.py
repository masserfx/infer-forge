"""OrderEmbedding model for vector similarity search."""

from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPKMixin


class OrderEmbedding(Base, UUIDPKMixin, TimestampMixin):
    """Stores vector embeddings for orders to enable similarity search."""

    __tablename__ = "order_embeddings"

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    embedding: Mapped[list[float]] = mapped_column(
        Vector(384),
        nullable=False,
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="embedding")  # type: ignore[name-defined] # noqa: F821

    def __repr__(self) -> str:
        return f"<OrderEmbedding(id={self.id}, order_id={self.order_id})>"
