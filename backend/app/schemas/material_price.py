"""Pydantic schemas for material price management."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class MaterialPriceCreate(BaseModel):
    """Schema for creating a new material price."""

    name: str = Field(..., max_length=255, description="Název materiálu")
    specification: str | None = Field(None, max_length=255, description="Specifikace")
    material_grade: str | None = Field(None, max_length=100, description="Třída materiálu")
    form: str | None = Field(None, max_length=100, description="Forma materiálu")
    dimension: str | None = Field(None, max_length=255, description="Rozměry")
    unit: str = Field("kg", max_length=20, description="Jednotka")
    unit_price: Decimal = Field(..., ge=0, description="Jednotková cena v CZK")
    supplier: str | None = Field(None, max_length=255, description="Dodavatel")
    valid_from: date = Field(..., description="Platnost od")
    valid_to: date | None = Field(None, description="Platnost do (NULL = neomezeně)")
    is_active: bool = Field(True, description="Aktivní cena")
    notes: str | None = Field(None, description="Poznámky")


class MaterialPriceUpdate(BaseModel):
    """Schema for updating an existing material price."""

    name: str | None = Field(None, max_length=255)
    specification: str | None = Field(None, max_length=255)
    material_grade: str | None = Field(None, max_length=100)
    form: str | None = Field(None, max_length=100)
    dimension: str | None = Field(None, max_length=255)
    unit: str | None = Field(None, max_length=20)
    unit_price: Decimal | None = Field(None, ge=0)
    supplier: str | None = Field(None, max_length=255)
    valid_from: date | None = None
    valid_to: date | None = None
    is_active: bool | None = None
    notes: str | None = None


class MaterialPriceResponse(BaseModel):
    """Schema for material price response."""

    id: UUID
    name: str
    specification: str | None
    material_grade: str | None
    form: str | None
    dimension: str | None
    unit: str
    unit_price: Decimal
    supplier: str | None
    valid_from: date
    valid_to: date | None
    is_active: bool
    notes: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class MaterialPriceListResponse(BaseModel):
    """Schema for paginated material price list."""

    items: list[MaterialPriceResponse]
    total: int
    skip: int
    limit: int


class MaterialPriceImportRow(BaseModel):
    """Schema for a single row in Excel import."""

    name: str
    specification: str | None = None
    material_grade: str | None = None
    form: str | None = None
    dimension: str | None = None
    unit: str = "kg"
    unit_price: Decimal
    supplier: str | None = None
    valid_from: date
    valid_to: date | None = None
    is_active: bool = True
    notes: str | None = None


class MaterialPriceImportResult(BaseModel):
    """Schema for Excel import result."""

    success: bool
    imported_count: int
    failed_count: int
    errors: list[str] = Field(default_factory=list)
