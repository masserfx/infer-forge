"""Pohoda integration Pydantic schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.pohoda_sync import SyncDirection, SyncStatus


class PohodaSyncRequest(BaseModel):
    """Request to sync an entity with Pohoda."""

    entity_type: str = Field(
        ...,
        pattern="^(customer|order|offer|invoice)$",
        description="Entity type to sync (customer, order, offer, invoice)",
    )
    entity_id: UUID = Field(..., description="Entity UUID to sync")


class InvoiceGenerateRequest(BaseModel):
    """Request to generate invoice for an order."""

    invoice_number: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Invoice number (e.g., FV-2025-001)",
    )
    invoice_date: date | None = Field(
        None,
        description="Invoice issue date (defaults to today)",
    )
    due_days: int = Field(
        14,
        ge=1,
        le=365,
        description="Payment due in days (default 14)",
    )


class PohodaSyncLogResponse(BaseModel):
    """Response schema for Pohoda sync log entry."""

    id: UUID
    entity_type: str
    entity_id: UUID
    direction: SyncDirection
    pohoda_doc_number: str | None = None
    status: SyncStatus
    error_message: str | None = None
    synced_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PohodaSyncResult(BaseModel):
    """Result of a sync operation."""

    success: bool
    sync_log_id: UUID
    pohoda_id: int | None = None
    pohoda_doc_number: str | None = None
    error: str | None = None


class PohodaSyncStatusResponse(BaseModel):
    """Status of Pohoda sync for an entity."""

    entity_type: str
    entity_id: UUID
    last_sync: PohodaSyncLogResponse | None = None
    sync_count: int = 0
    last_success: datetime | None = None
