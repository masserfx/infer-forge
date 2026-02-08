"""Subcontractor and Subcontract Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# --- Subcontractor schemas ---


class SubcontractorBase(BaseModel):
    """Base subcontractor schema with shared fields."""

    name: str = Field(..., max_length=255, description="Subcontractor name")
    ico: str | None = Field(None, max_length=20, description="Company registration number")
    contact_email: EmailStr | None = Field(None, description="Contact email")
    contact_phone: str | None = Field(None, max_length=50, description="Contact phone")
    specialization: str | None = Field(
        None,
        max_length=255,
        description="Specialization (e.g. svařování, NDT, povrchová úprava)",
    )
    rating: int | None = Field(None, ge=1, le=5, description="Rating 1-5")
    is_active: bool = Field(True, description="Is subcontractor active")
    notes: str | None = Field(None, description="Notes")


class SubcontractorCreate(SubcontractorBase):
    """Schema for creating a new subcontractor."""

    pass


class SubcontractorUpdate(BaseModel):
    """Schema for updating an existing subcontractor."""

    name: str | None = Field(None, max_length=255)
    ico: str | None = Field(None, max_length=20)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(None, max_length=50)
    specialization: str | None = Field(None, max_length=255)
    rating: int | None = Field(None, ge=1, le=5)
    is_active: bool | None = None
    notes: str | None = None


class SubcontractorResponse(SubcontractorBase):
    """Schema for subcontractor responses."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubcontractorListResponse(BaseModel):
    """Schema for subcontractor list responses."""

    items: list[SubcontractorResponse]
    total: int


# --- Subcontract schemas ---


class SubcontractBase(BaseModel):
    """Base subcontract schema with shared fields."""

    subcontractor_id: UUID = Field(..., description="Subcontractor ID")
    description: str = Field(..., description="Subcontract description")
    price: Decimal | None = Field(None, ge=Decimal("0.00"), description="Price")
    status: str = Field("requested", description="Status")
    planned_start: datetime | None = Field(None, description="Planned start date")
    planned_end: datetime | None = Field(None, description="Planned end date")
    actual_end: datetime | None = Field(None, description="Actual end date")
    notes: str | None = Field(None, description="Notes")


class SubcontractCreate(SubcontractBase):
    """Schema for creating a new subcontract."""

    pass


class SubcontractUpdate(BaseModel):
    """Schema for updating an existing subcontract."""

    subcontractor_id: UUID | None = None
    description: str | None = None
    price: Decimal | None = Field(None, ge=Decimal("0.00"))
    status: str | None = None
    planned_start: datetime | None = None
    planned_end: datetime | None = None
    actual_end: datetime | None = None
    notes: str | None = None


class SubcontractResponse(SubcontractBase):
    """Schema for subcontract responses."""

    id: UUID
    order_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubcontractListResponse(BaseModel):
    """Schema for subcontract list responses."""

    items: list[SubcontractResponse]
    total: int
