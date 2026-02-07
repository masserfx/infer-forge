"""Pydantic schemas for INFER FORGE API."""

from .customer import CustomerCreate, CustomerResponse, CustomerUpdate
from .inbox import InboxAssign, InboxMessageResponse, InboxReclassify
from .order import (
    OrderCreate,
    OrderItemCreate,
    OrderItemResponse,
    OrderResponse,
    OrderStatusUpdate,
    OrderUpdate,
)

__all__ = [
    # Customer
    "CustomerCreate",
    "CustomerUpdate",
    "CustomerResponse",
    # Order
    "OrderCreate",
    "OrderUpdate",
    "OrderResponse",
    "OrderStatusUpdate",
    "OrderItemCreate",
    "OrderItemResponse",
    # Inbox
    "InboxMessageResponse",
    "InboxAssign",
    "InboxReclassify",
]
