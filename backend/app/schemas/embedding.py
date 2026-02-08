"""Pydantic schemas for embedding similarity search."""

from pydantic import BaseModel, Field


class SimilarOrderResult(BaseModel):
    """A single similar order result."""

    order_id: str
    order_number: str
    status: str
    priority: str
    customer_name: str | None = None
    similarity: float = Field(ge=0.0, le=1.0, description="Cosine similarity 0-1")
    note: str | None = None

    model_config = {"from_attributes": True}


class SimilarOrdersResponse(BaseModel):
    """Response containing list of similar orders."""

    order_id: str
    similar_orders: list[SimilarOrderResult]
    total: int


class SimilarSearchRequest(BaseModel):
    """Request for text-based similarity search."""

    query: str = Field(min_length=3, max_length=2000, description="Search text in Czech")
    limit: int = Field(default=5, ge=1, le=20, description="Max results")
