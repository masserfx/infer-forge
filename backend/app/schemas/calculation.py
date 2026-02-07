"""Calculation Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import CalculationStatus, CostType


class CalculationItemCreate(BaseModel):
    """Schema for creating a calculation item."""

    cost_type: CostType = Field(..., description="Type of cost")
    name: str = Field(..., max_length=255, description="Item name")
    description: Optional[str] = Field(None, description="Item description")
    quantity: Decimal = Field(default=Decimal("1"), ge=0, description="Quantity")
    unit: str = Field(default="ks", max_length=20, description="Unit")
    unit_price: Decimal = Field(default=Decimal("0"), ge=0, description="Unit price in CZK")


class CalculationItemUpdate(BaseModel):
    """Schema for updating a calculation item."""

    cost_type: Optional[CostType] = None
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    quantity: Optional[Decimal] = Field(None, ge=0)
    unit: Optional[str] = Field(None, max_length=20)
    unit_price: Optional[Decimal] = Field(None, ge=0)


class CalculationItemResponse(BaseModel):
    """Schema for calculation item responses."""

    id: UUID
    calculation_id: UUID
    cost_type: CostType
    name: str
    description: Optional[str] = None
    quantity: Decimal
    unit: str
    unit_price: Decimal
    total_price: Decimal

    model_config = ConfigDict(from_attributes=True)


class CalculationCreate(BaseModel):
    """Schema for creating a calculation."""

    order_id: UUID = Field(..., description="Order UUID")
    name: str = Field(..., max_length=255, description="Calculation name")
    note: Optional[str] = Field(None, description="Notes")
    margin_percent: Decimal = Field(
        default=Decimal("15"), ge=0, le=100, description="Margin percentage"
    )
    items: list[CalculationItemCreate] = Field(
        default_factory=list, description="Initial calculation items"
    )


class CalculationUpdate(BaseModel):
    """Schema for updating a calculation."""

    name: Optional[str] = Field(None, max_length=255)
    note: Optional[str] = None
    margin_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    status: Optional[CalculationStatus] = None


class CalculationResponse(BaseModel):
    """Schema for calculation responses."""

    id: UUID
    order_id: UUID
    name: str
    status: CalculationStatus
    note: Optional[str] = None
    created_by: Optional[UUID] = None
    material_total: Decimal
    labor_total: Decimal
    cooperation_total: Decimal
    overhead_total: Decimal
    margin_percent: Decimal
    margin_amount: Decimal
    total_price: Decimal
    items: list[CalculationItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CalculationSummary(BaseModel):
    """Summary of calculation totals for dashboard views."""

    id: UUID
    order_id: UUID
    name: str
    status: CalculationStatus
    material_total: Decimal
    labor_total: Decimal
    cooperation_total: Decimal
    overhead_total: Decimal
    margin_percent: Decimal
    total_price: Decimal
    items_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
