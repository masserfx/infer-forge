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
    material: Optional[str] = Field(None, max_length=100, description="Material specification")
    quantity: Decimal = Field(..., ge=0, description="Quantity")
    unit: str = Field(default="ks", max_length=20, description="Unit of measurement")
    dn: Optional[str] = Field(None, max_length=20, description="Diameter Nominal")
    pn: Optional[str] = Field(None, max_length=20, description="Pressure Nominal")
    note: Optional[str] = Field(None, description="Additional notes")
    drawing_url: Optional[str] = Field(None, max_length=512, description="URL to technical drawing")


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
    due_date: Optional[date] = Field(None, description="Due date")
    note: Optional[str] = Field(None, description="Order notes")


class OrderCreate(OrderBase):
    """Schema for creating a new order."""

    items: list[OrderItemCreate] = Field(default_factory=list, description="Order items")


class OrderUpdate(BaseModel):
    """Schema for updating an existing order.

    All fields are optional to support partial updates.
    """

    customer_id: Optional[UUID] = None
    number: Optional[str] = Field(None, max_length=50)
    status: Optional[OrderStatus] = None
    priority: Optional[OrderPriority] = None
    due_date: Optional[date] = None
    note: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    """Schema for updating order status."""

    status: OrderStatus = Field(..., description="New order status")


class OrderResponse(OrderBase):
    """Schema for order responses."""

    id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = Field(default_factory=list)
    customer: Optional["CustomerResponse"] = None

    model_config = ConfigDict(from_attributes=True)


# Import after class definitions to avoid circular imports
from app.schemas.customer import CustomerResponse  # noqa: E402

OrderResponse.model_rebuild()
