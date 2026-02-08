"""Customer Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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
    category: str | None = Field(
        "C",
        max_length=1,
        description="Customer category: A=Klíčový, B=Běžný, C=Nový/jednorázový",
    )
    discount_percent: Decimal | None = Field(
        Decimal("0.00"),
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        description="Discount percentage (0.00-100.00)",
    )
    payment_terms_days: int | None = Field(
        14,
        ge=0,
        description="Payment terms in days",
    )
    credit_limit: Decimal | None = Field(
        None,
        ge=Decimal("0.00"),
        description="Customer credit limit",
    )
    notes: str | None = Field(None, description="Internal notes about the customer")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        """Validate customer category is A, B, or C."""
        if v is not None and v not in ("A", "B", "C"):
            raise ValueError("Category must be A, B, or C")
        return v


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
    category: str | None = Field(None, max_length=1)
    discount_percent: Decimal | None = Field(None, ge=Decimal("0.00"), le=Decimal("100.00"))
    payment_terms_days: int | None = Field(None, ge=0)
    credit_limit: Decimal | None = Field(None, ge=Decimal("0.00"))
    notes: str | None = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        """Validate customer category is A, B, or C."""
        if v is not None and v not in ("A", "B", "C"):
            raise ValueError("Category must be A, B, or C")
        return v


class CustomerCategoryUpdate(BaseModel):
    """Schema for updating customer category only."""

    category: str = Field(..., max_length=1, description="Customer category: A, B, or C")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate customer category is A, B, or C."""
        if v not in ("A", "B", "C"):
            raise ValueError("Category must be A, B, or C")
        return v


class CustomerResponse(CustomerBase):
    """Schema for customer responses."""

    id: UUID
    pohoda_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
