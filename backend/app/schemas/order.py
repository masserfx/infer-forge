"""Order Pydantic schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import OrderPriority, OrderStatus


class OrderItemBase(BaseModel):
    """Base order item schema with shared fields."""

    name: str = Field(..., max_length=255, description="Item name/description")
    material: str | None = Field(None, max_length=100, description="Material specification")
    quantity: Decimal = Field(..., ge=0, description="Quantity")
    unit: str = Field(default="ks", max_length=20, description="Unit of measurement")
    dn: str | None = Field(None, max_length=20, description="Diameter Nominal")
    pn: str | None = Field(None, max_length=20, description="Pressure Nominal")
    note: str | None = Field(None, description="Additional notes")
    drawing_url: str | None = Field(None, max_length=512, description="URL to technical drawing")


class OrderItemCreate(OrderItemBase):
    """Schema for creating a new order item."""

    pass


class OrderItemResponse(OrderItemBase):
    """Schema for order item responses."""

    id: UUID

    model_config = ConfigDict(from_attributes=True)


class OrderBase(BaseModel):
    """Base order schema with shared fields."""

    customer_id: UUID = Field(..., description="Customer UUID")
    number: str = Field(..., max_length=50, description="Order number")
    status: OrderStatus = Field(default=OrderStatus.POPTAVKA, description="Order status")
    priority: OrderPriority = Field(default=OrderPriority.NORMAL, description="Order priority")
    due_date: date | None = Field(None, description="Due date")
    note: str | None = Field(None, description="Order notes")


class OrderCreate(OrderBase):
    """Schema for creating a new order."""

    items: list[OrderItemCreate] = Field(default_factory=list, description="Order items")


class OrderUpdate(BaseModel):
    """Schema for updating an existing order.

    All fields are optional to support partial updates.
    """

    customer_id: UUID | None = None
    number: str | None = Field(None, max_length=50)
    status: OrderStatus | None = None
    priority: OrderPriority | None = None
    due_date: date | None = None
    note: str | None = None


class OrderStatusUpdate(BaseModel):
    """Schema for updating order status."""

    status: OrderStatus = Field(..., description="New order status")


class OrderResponse(OrderBase):
    """Schema for order responses."""

    id: UUID
    created_by: UUID | None = None
    assigned_to: UUID | None = None
    assigned_to_name: str | None = None
    created_at: datetime
    updated_at: datetime
    source_offer_id: UUID | None = Field(None, description="ID of source offer if converted")
    items: list[OrderItemResponse] = Field(default_factory=list)
    customer: Optional["CustomerResponse"] = None

    model_config = ConfigDict(from_attributes=True)


# Import after class definitions to avoid circular imports
from app.schemas.customer import CustomerResponse  # noqa: E402

OrderResponse.model_rebuild()
