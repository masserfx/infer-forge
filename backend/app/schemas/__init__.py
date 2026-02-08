"""Pydantic schemas for INFER FORGE API."""

from .auth import (
    LoginRequest,
    PasswordChange,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from .calculation import (
    CalculationCreate,
    CalculationItemCreate,
    CalculationItemResponse,
    CalculationItemUpdate,
    CalculationResponse,
    CalculationSummary,
    CalculationUpdate,
)
from .customer import (
    CustomerCategoryUpdate,
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
)
from .document import DocumentResponse, DocumentUpdate, DocumentUpload
from .drawing import (
    DrawingAnalysisResponse,
    DrawingDimensionSchema,
    DrawingMaterialSchema,
    DrawingToleranceSchema,
    WeldingRequirementsSchema,
)
from .embedding import SimilarOrderResult, SimilarOrdersResponse, SimilarSearchRequest
from .inbox import InboxAssign, InboxMessageResponse, InboxReclassify
from .material_price import (
    MaterialPriceCreate,
    MaterialPriceImportResult,
    MaterialPriceListResponse,
    MaterialPriceResponse,
    MaterialPriceUpdate,
)
from .notification import NotificationCreate, NotificationList, NotificationResponse
from .operation import (
    OperationCreate,
    OperationListResponse,
    OperationReorderRequest,
    OperationResponse,
    OperationUpdate,
)
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
from .reporting import (
    CustomerReport,
    DashboardStats,
    MaterialRequirementItem,
    MaterialRequirementsResponse,
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
    # Drawing Analysis
    "DrawingAnalysisResponse",
    "DrawingDimensionSchema",
    "DrawingMaterialSchema",
    "DrawingToleranceSchema",
    "WeldingRequirementsSchema",
    # Customer
    "CustomerCreate",
    "CustomerUpdate",
    "CustomerCategoryUpdate",
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
    # MaterialPrice
    "MaterialPriceCreate",
    "MaterialPriceUpdate",
    "MaterialPriceResponse",
    "MaterialPriceListResponse",
    "MaterialPriceImportResult",
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
    "MaterialRequirementItem",
    "MaterialRequirementsResponse",
    # Embedding
    "SimilarOrderResult",
    "SimilarOrdersResponse",
    "SimilarSearchRequest",
    # Notification
    "NotificationCreate",
    "NotificationResponse",
    "NotificationList",
    # Operation
    "OperationCreate",
    "OperationUpdate",
    "OperationResponse",
    "OperationListResponse",
    "OperationReorderRequest",
]
