"""Embedding service for order similarity search using pgvector."""

import hashlib
import logging
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order
from app.models.order_embedding import OrderEmbedding
from app.schemas.embedding import SimilarOrderResult

logger = logging.getLogger(__name__)

# Singleton model cache
_model_instance = None


def _get_model():  # type: ignore[no-untyped-def]
    """Get or initialize the sentence-transformers model (singleton)."""
    global _model_instance  # noqa: PLW0603
    if _model_instance is None:
        from sentence_transformers import SentenceTransformer

        _model_instance = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        logger.info("embedding_model_loaded model=paraphrase-multilingual-MiniLM-L12-v2")
    return _model_instance


def extract_order_text(order: Order) -> str:
    """Extract searchable text from an order for embedding.

    Args:
        order: Order instance with items loaded.

    Returns:
        Concatenated text representation of the order.
    """
    parts = [
        f"Zakázka {order.number}",
        f"Stav: {order.status.value}",
        f"Priorita: {order.priority.value}",
    ]

    if order.note:
        parts.append(f"Poznámka: {order.note}")

    # Include items
    if hasattr(order, "items") and order.items:
        for item in order.items:
            item_parts = [f"Položka: {item.name}"]
            if item.material:
                item_parts.append(f"materiál {item.material}")
            if item.dn:
                item_parts.append(f"DN{item.dn}")
            if item.pn:
                item_parts.append(f"PN{item.pn}")
            if item.note:
                item_parts.append(item.note)
            parts.append(", ".join(item_parts))

    return "\n".join(parts)


def compute_content_hash(text: str) -> str:
    """Compute SHA256 hash of text content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class EmbeddingService:
    """Service for generating and searching order embeddings."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_embedding(self, order_id: UUID) -> OrderEmbedding | None:
        """Generate or update embedding for an order.

        Args:
            order_id: Order UUID.

        Returns:
            OrderEmbedding instance or None if order not found.
        """
        # Load order with items
        result = await self.db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items))
        )
        order = result.scalar_one_or_none()
        if not order:
            logger.warning("generate_embedding.order_not_found order_id=%s", order_id)
            return None

        # Extract text and compute hash
        text_content = extract_order_text(order)
        content_hash = compute_content_hash(text_content)

        # Check if embedding already exists with same hash
        existing_result = await self.db.execute(
            select(OrderEmbedding).where(OrderEmbedding.order_id == order_id)
        )
        existing = existing_result.scalar_one_or_none()

        if existing and existing.content_hash == content_hash:
            logger.info("generate_embedding.unchanged order_id=%s", order_id)
            return existing

        # Generate embedding vector
        model = _get_model()
        vector = model.encode(text_content).tolist()

        if existing:
            # Update existing embedding
            existing.embedding = vector
            existing.content_hash = content_hash
            existing.text_content = text_content
            await self.db.flush()
            logger.info("generate_embedding.updated order_id=%s", order_id)
            return existing
        else:
            # Create new embedding
            embedding = OrderEmbedding(
                order_id=order_id,
                embedding=vector,
                content_hash=content_hash,
                text_content=text_content,
            )
            self.db.add(embedding)
            await self.db.flush()
            logger.info("generate_embedding.created order_id=%s", order_id)
            return embedding

    async def find_similar(
        self,
        order_id: UUID,
        limit: int = 5,
    ) -> list[SimilarOrderResult]:
        """Find similar orders by vector similarity.

        Args:
            order_id: Reference order UUID.
            limit: Max results.

        Returns:
            List of similar order results sorted by similarity.
        """
        # Get the reference embedding
        result = await self.db.execute(
            select(OrderEmbedding).where(OrderEmbedding.order_id == order_id)
        )
        reference = result.scalar_one_or_none()
        if not reference:
            return []

        # Use pgvector cosine distance operator <=>
        query = text("""
            SELECT
                oe.order_id,
                o.number as order_number,
                o.status,
                o.priority,
                o.note,
                c.company_name as customer_name,
                1 - (oe.embedding <=> :ref_embedding) as similarity
            FROM order_embeddings oe
            JOIN orders o ON o.id = oe.order_id
            LEFT JOIN customers c ON c.id = o.customer_id
            WHERE oe.order_id != :order_id
            ORDER BY oe.embedding <=> :ref_embedding
            LIMIT :limit
        """)

        result = await self.db.execute(
            query,
            {
                "ref_embedding": str(reference.embedding),
                "order_id": str(order_id),
                "limit": limit,
            },
        )

        rows = result.fetchall()
        return [
            SimilarOrderResult(
                order_id=str(row.order_id),
                order_number=row.order_number,
                status=row.status,
                priority=row.priority,
                customer_name=row.customer_name,
                similarity=max(0.0, min(1.0, float(row.similarity))),
                note=row.note,
            )
            for row in rows
        ]

    async def search_by_text(
        self,
        query_text: str,
        limit: int = 5,
    ) -> list[SimilarOrderResult]:
        """Search orders by text similarity.

        Args:
            query_text: Search query in natural language.
            limit: Max results.

        Returns:
            List of similar order results.
        """
        # Generate embedding for query
        model = _get_model()
        query_vector = model.encode(query_text).tolist()

        query = text("""
            SELECT
                oe.order_id,
                o.number as order_number,
                o.status,
                o.priority,
                o.note,
                c.company_name as customer_name,
                1 - (oe.embedding <=> :query_vector) as similarity
            FROM order_embeddings oe
            JOIN orders o ON o.id = oe.order_id
            LEFT JOIN customers c ON c.id = o.customer_id
            ORDER BY oe.embedding <=> :query_vector
            LIMIT :limit
        """)

        result = await self.db.execute(
            query,
            {
                "query_vector": str(query_vector),
                "limit": limit,
            },
        )

        rows = result.fetchall()
        return [
            SimilarOrderResult(
                order_id=str(row.order_id),
                order_number=row.order_number,
                status=row.status,
                priority=row.priority,
                customer_name=row.customer_name,
                similarity=max(0.0, min(1.0, float(row.similarity))),
                note=row.note,
            )
            for row in rows
        ]
