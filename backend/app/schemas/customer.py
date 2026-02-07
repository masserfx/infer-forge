"""Customer Pydantic schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerBase(BaseModel):
    """Base customer schema with shared fields."""

    company_name: str = Field(..., max_length=255, description="Company name")
    ico: str = Field(..., min_length=8, max_length=8, description="Company registration number (IČO)")
    dic: Optional[str] = Field(None, max_length=20, description="Tax identification number (DIČ)")
    contact_name: str = Field(..., max_length=255, description="Contact person name")
    email: EmailStr = Field(..., description="Contact email address")
    phone: Optional[str] = Field(None, max_length=50, description="Contact phone number")
    address: Optional[str] = Field(None, description="Company address")


class CustomerCreate(CustomerBase):
    """Schema for creating a new customer."""

    pass


class CustomerUpdate(BaseModel):
    """Schema for updating an existing customer.

    All fields are optional to support partial updates.
    """

    company_name: Optional[str] = Field(None, max_length=255)
    ico: Optional[str] = Field(None, min_length=8, max_length=8)
    dic: Optional[str] = Field(None, max_length=20)
    contact_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None


class CustomerResponse(CustomerBase):
    """Schema for customer responses."""

    id: UUID
    pohoda_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
