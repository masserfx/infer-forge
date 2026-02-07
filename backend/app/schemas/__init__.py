"""Pydantic schemas for INFER FORGE API."""

from .calculation import (
    CalculationCreate,
    CalculationItemCreate,
    CalculationItemResponse,
    CalculationItemUpdate,
    CalculationResponse,
    CalculationSummary,
    CalculationUpdate,
)
from .customer import CustomerCreate, CustomerResponse, CustomerUpdate
from .document import DocumentResponse, DocumentUpdate, DocumentUpload
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
from .auth import (
    LoginRequest,
    PasswordChange,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from .reporting import (
    CustomerReport,
    DashboardStats,
    PipelineReport,
    ProductionReport,
    RevenueReport,
)

__all__ = [
    # Calculation
    "CalculationCreate",
    "CalculationUpdate",
    "CalculationResponse",
    "CalculationSummary",
    "CalculationItemCreate",
    "CalculationItemUpdate",
    "CalculationItemResponse",
    # Document
    "DocumentUpload",
    "DocumentUpdate",
    "DocumentResponse",
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
    # Auth
    "LoginRequest",
    "TokenResponse",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "PasswordChange",
    # Reporting
    "DashboardStats",
    "PipelineReport",
    "RevenueReport",
    "ProductionReport",
    "CustomerReport",
]
