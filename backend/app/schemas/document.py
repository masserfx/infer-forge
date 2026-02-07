"""Document Pydantic schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import DocumentCategory


class DocumentUpload(BaseModel):
    """Schema for document upload metadata (sent alongside file)."""

    entity_type: str = Field(..., max_length=50, description="Entity type (order, customer, offer)")
    entity_id: UUID = Field(..., description="Entity UUID")
    category: DocumentCategory = Field(
        default=DocumentCategory.OSTATNI, description="Document category"
    )
    description: Optional[str] = Field(None, description="Document description")


class DocumentUpdate(BaseModel):
    """Schema for updating document metadata."""

    category: Optional[DocumentCategory] = None
    description: Optional[str] = None


class DocumentResponse(BaseModel):
    """Schema for document responses."""

    id: UUID
    entity_type: str
    entity_id: UUID
    file_name: str
    file_path: str
    mime_type: str
    file_size: int
    version: int
    category: DocumentCategory
    description: Optional[str] = None
    ocr_text: Optional[str] = None
    uploaded_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
