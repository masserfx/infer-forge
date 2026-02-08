"""Pydantic schemas for Operation API."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import ValidationInfo


class OperationCreate(BaseModel):
    """Schema for creating a new operation."""

    name: str = Field(..., min_length=1, max_length=255, description="Operation name")
    description: str | None = Field(None, description="Detailed description")
    sequence: int = Field(..., ge=1, description="Sequence order (1, 2, 3...)")
    duration_hours: Decimal | None = Field(
        None,
        ge=0,
        decimal_places=2,
        description="Estimated duration in hours",
    )
    responsible: str | None = Field(
        None,
        max_length=255,
        description="Responsible person/team",
    )
    planned_start: datetime | None = Field(None, description="Planned start datetime")
    planned_end: datetime | None = Field(None, description="Planned end datetime")
    notes: str | None = Field(None, description="Additional notes")

    @field_validator("planned_end")
    @classmethod
    def validate_planned_dates(cls, v: datetime | None, info: ValidationInfo) -> datetime | None:
        """Validate that planned_end is after planned_start."""
        if v is not None and "planned_start" in info.data:
            planned_start = info.data.get("planned_start")
            if planned_start is not None and v <= planned_start:
                raise ValueError("planned_end must be after planned_start")
        return v


class OperationUpdate(BaseModel):
    """Schema for updating an existing operation."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    sequence: int | None = Field(None, ge=1)
    duration_hours: Decimal | None = Field(None, ge=0, decimal_places=2)
    responsible: str | None = Field(None, max_length=255)
    planned_start: datetime | None = None
    planned_end: datetime | None = None
    actual_start: datetime | None = None
    actual_end: datetime | None = None
    status: str | None = Field(
        None,
        pattern="^(planned|in_progress|completed|cancelled)$",
        description="Operation status",
    )
    notes: str | None = None


class OperationResponse(BaseModel):
    """Schema for operation response."""

    id: UUID
    order_id: UUID
    name: str
    description: str | None
    sequence: int
    duration_hours: Decimal | None
    responsible: str | None
    planned_start: datetime | None
    planned_end: datetime | None
    actual_start: datetime | None
    actual_end: datetime | None
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OperationListResponse(BaseModel):
    """Schema for list of operations."""

    items: list[OperationResponse]
    total: int


class OperationReorderRequest(BaseModel):
    """Schema for reordering operations."""

    operation_ids: list[UUID] = Field(
        ...,
        min_length=1,
        description="List of operation IDs in new order",
    )
