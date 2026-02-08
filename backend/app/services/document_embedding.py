"""Document embedding service for RAG semantic search.

Provides semantic search over OCR-extracted text from documents using
sentence-transformers and pgvector. Falls back to LIKE queries if pgvector
is unavailable.
"""

import hashlib
import logging
from uuid import UUID

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_embedding import DocumentEmbedding

logger = logging.getLogger(__name__)

# Singleton model cache
_model_instance = None

# Token limit per chunk (approx. 512 tokens = ~2000 chars in Czech/English)
_CHUNK_SIZE_CHARS: int = 2000
_CHUNK_OVERLAP_CHARS: int = 200


def _get_model():  # type: ignore[no-untyped-def]
    """Get or initialize the sentence-transformers model (singleton).

    Returns:
        SentenceTransformer model instance for multilingual embeddings.
    """
    global _model_instance  # noqa: PLW0603
    if _model_instance is None:
        from sentence_transformers import SentenceTransformer

        _model_instance = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        logger.info("embedding_model_loaded model=paraphrase-multilingual-MiniLM-L12-v2 dim=384")
    return _model_instance


def _chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks of approximately 512 tokens.

    Args:
        text: Full text content to chunk.

    Returns:
        List of text chunks with overlap for context preservation.
    """
    if len(text) <= _CHUNK_SIZE_CHARS:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = start + _CHUNK_SIZE_CHARS
        chunk = text[start:end]

        # Try to break on sentence boundary (period + space)
        if end < len(text):
            last_period = chunk.rfind(". ")
            if last_period > _CHUNK_SIZE_CHARS // 2:
                chunk = chunk[: last_period + 1]
                end = start + last_period + 1

        chunks.append(chunk.strip())
        start = end - _CHUNK_OVERLAP_CHARS

    return chunks


def _compute_content_hash(text: str) -> str:
    """Compute SHA256 hash of text content.

    Args:
        text: Text content to hash.

    Returns:
        Hex-encoded SHA256 hash.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class DocumentEmbeddingService:
    """Service for generating and searching document embeddings.

    Provides semantic search over OCR-extracted document text using pgvector.
    Falls back to SQL LIKE search if pgvector is unavailable.

    Args:
        db: SQLAlchemy async session.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_embedding(
        self,
        document_id: UUID,
        content: str,
        metadata: dict | None = None,
    ) -> list[DocumentEmbedding]:
        """Create embeddings for a document by chunking and embedding its content.

        Args:
            document_id: UUID of the document.
            content: Full text content (e.g., OCR output).
            metadata: Optional metadata to store with each chunk.

        Returns:
            List of created DocumentEmbedding instances.
        """
        if not content or not content.strip():
            logger.warning("create_embedding.empty_content document_id=%s", document_id)
            return []

        # Delete existing embeddings for this document
        await self.delete_by_document(document_id)

        # Chunk the content
        chunks = _chunk_text(content)
        logger.info(
            "create_embedding.chunked document_id=%s chunks=%d", document_id, len(chunks)
        )

        # Generate embeddings for each chunk
        model = _get_model()
        embeddings: list[DocumentEmbedding] = []

        for idx, chunk in enumerate(chunks):
            vector = model.encode(chunk).tolist()
            embedding = DocumentEmbedding(
                document_id=document_id,
                chunk_index=idx,
                content_chunk=chunk,
                embedding=vector,
                metadata_json=metadata,
            )
            self.db.add(embedding)
            embeddings.append(embedding)

        await self.db.flush()
        logger.info(
            "create_embedding.created document_id=%s embeddings=%d", document_id, len(embeddings)
        )
        return embeddings

    async def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """Search documents by semantic similarity to query text.

        Args:
            query: Natural language search query.
            limit: Maximum number of results to return.

        Returns:
            List of dicts with document_id, chunk_index, content_chunk, similarity.
        """
        if not query or not query.strip():
            logger.warning("search.empty_query")
            return []

        # Try pgvector search first
        try:
            return await self._search_with_pgvector(query, limit)
        except Exception:
            logger.warning("search.pgvector_unavailable query=%s", query[:50])
            # Fallback to LIKE search
            return await self._search_with_like(query, limit)

    async def _search_with_pgvector(self, query: str, limit: int) -> list[dict]:
        """Search using pgvector cosine similarity.

        Args:
            query: Search query text.
            limit: Max results.

        Returns:
            List of search results with similarity scores.
        """
        # Generate query embedding
        model = _get_model()
        query_vector = model.encode(query).tolist()

        # Use pgvector cosine distance operator <=>
        sql = text("""
            SELECT
                de.document_id,
                de.chunk_index,
                de.content_chunk,
                d.filename,
                d.document_type,
                1 - (de.embedding <=> :query_vector) as similarity
            FROM document_embeddings de
            JOIN documents d ON d.id = de.document_id
            ORDER BY de.embedding <=> :query_vector
            LIMIT :limit
        """)

        result = await self.db.execute(
            sql,
            {
                "query_vector": str(query_vector),
                "limit": limit,
            },
        )

        rows = result.fetchall()
        logger.info("search.pgvector_results query=%s results=%d", query[:50], len(rows))

        return [
            {
                "document_id": str(row.document_id),
                "chunk_index": row.chunk_index,
                "content_chunk": row.content_chunk,
                "filename": row.filename,
                "document_type": row.document_type,
                "similarity": max(0.0, min(1.0, float(row.similarity))),
            }
            for row in rows
        ]

    async def _search_with_like(self, query: str, limit: int) -> list[dict]:
        """Fallback search using SQL LIKE pattern matching.

        Args:
            query: Search query text.
            limit: Max results.

        Returns:
            List of search results without similarity scores.
        """
        # Split query into keywords
        keywords = [kw.strip() for kw in query.split() if len(kw.strip()) > 2]
        if not keywords:
            return []

        # Build LIKE filters
        filters = [
            DocumentEmbedding.content_chunk.ilike(f"%{kw}%") for kw in keywords[:5]  # Max 5 keywords
        ]

        stmt = (
            select(DocumentEmbedding, Document.filename, Document.document_type)
            .join(Document, DocumentEmbedding.document_id == Document.id)
            .where(or_(*filters))
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        rows = result.fetchall()
        logger.info("search.like_results query=%s results=%d", query[:50], len(rows))

        return [
            {
                "document_id": str(row.DocumentEmbedding.document_id),
                "chunk_index": row.DocumentEmbedding.chunk_index,
                "content_chunk": row.DocumentEmbedding.content_chunk,
                "filename": row.filename,
                "document_type": row.document_type,
                "similarity": 0.5,  # Default similarity for LIKE results
            }
            for row in rows
        ]

    async def delete_by_document(self, document_id: UUID) -> int:
        """Delete all embeddings for a specific document.

        Args:
            document_id: UUID of the document.

        Returns:
            Number of deleted embeddings.
        """
        stmt = select(DocumentEmbedding).where(DocumentEmbedding.document_id == document_id)
        result = await self.db.execute(stmt)
        embeddings = result.scalars().all()

        for embedding in embeddings:
            await self.db.delete(embedding)

        await self.db.flush()
        logger.info("delete_by_document document_id=%s deleted=%d", document_id, len(embeddings))
        return len(embeddings)
