"""Pohoda integration Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.pohoda_sync import SyncDirection, SyncStatus


class PohodaSyncRequest(BaseModel):
    """Request to sync an entity with Pohoda."""

    entity_type: str = Field(
        ...,
        pattern="^(customer|order|offer)$",
        description="Entity type to sync (customer, order, offer)",
    )
    entity_id: UUID = Field(..., description="Entity UUID to sync")


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
