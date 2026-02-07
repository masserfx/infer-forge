"""Customer Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerBase(BaseModel):
    """Base customer schema with shared fields."""

    company_name: str = Field(..., max_length=255, description="Company name")
    ico: str = Field(
        ..., min_length=8, max_length=8, description="Company registration number (IČO)"
    )
    dic: str | None = Field(None, max_length=20, description="Tax identification number (DIČ)")
    contact_name: str = Field(..., max_length=255, description="Contact person name")
    email: EmailStr = Field(..., description="Contact email address")
    phone: str | None = Field(None, max_length=50, description="Contact phone number")
    address: str | None = Field(None, description="Company address")


class CustomerCreate(CustomerBase):
    """Schema for creating a new customer."""

    pass


class CustomerUpdate(BaseModel):
    """Schema for updating an existing customer.

    All fields are optional to support partial updates.
    """

    company_name: str | None = Field(None, max_length=255)
    ico: str | None = Field(None, min_length=8, max_length=8)
    dic: str | None = Field(None, max_length=20)
    contact_name: str | None = Field(None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    address: str | None = None


class CustomerResponse(CustomerBase):
    """Schema for customer responses."""

    id: UUID
    pohoda_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
