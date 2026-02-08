"""Document embedding model for RAG semantic search."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSON as PGJSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None


class DocumentEmbedding(Base):
    """Stores document content chunks with vector embeddings.

    Used for semantic search across OCR-extracted text from documents.
    Each document is chunked into ~512-token blocks and embedded using
    sentence-transformers (multilingual model).
    """

    __tablename__ = "document_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_chunk: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(
        Vector(384) if Vector else Text,
        nullable=True,
    )
    metadata_json: Mapped[dict | None] = mapped_column(PGJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
