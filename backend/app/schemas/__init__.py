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
from .pohoda import (
    PohodaSyncLogResponse,
    PohodaSyncRequest,
    PohodaSyncResult,
    PohodaSyncStatusResponse,
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
    # Pohoda
    "PohodaSyncRequest",
    "PohodaSyncLogResponse",
    "PohodaSyncResult",
    "PohodaSyncStatusResponse",
]
