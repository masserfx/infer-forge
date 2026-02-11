"""SQLAlchemy models for inferbox."""

from .audit import AuditAction, AuditLog
from .base import Base, TimestampMixin, UUIDPKMixin
from .calculation import Calculation, CalculationItem, CalculationStatus, CostType
from .calculation_feedback import CalculationFeedback, CorrectionType
from .classification_feedback import ClassificationFeedback
from .customer import Customer
from .dead_letter import DeadLetterEntry
from .document import Document, DocumentCategory
from .document_embedding import DocumentEmbedding
from .drawing_analysis import DrawingAnalysis
from .email_attachment import EmailAttachment, OCRStatus
from .inbox import InboxClassification, InboxMessage, InboxStatus, MessageDirection
from .material_price import MaterialPrice
from .notification import Notification, NotificationType
from .offer import Offer, OfferStatus
from .operation import Operation, OperationStatus
from .order import Order, OrderItem, OrderPriority, OrderStatus
from .order_embedding import OrderEmbedding
from .pohoda_sync import PohodaSyncLog, SyncDirection, SyncStatus
from .processing_task import ProcessingStage, ProcessingStatus, ProcessingTask
from .subcontract import Subcontract, SubcontractStatus
from .subcontractor import Subcontractor
from .user import User, UserRole
from .user_points import PointsAction, PointsPeriod, UserPoints

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "UUIDPKMixin",
    # Calculation
    "Calculation",
    "CalculationItem",
    "CalculationStatus",
    "CostType",
    # Customer
    "Customer",
    # Order
    "Order",
    "OrderItem",
    "OrderStatus",
    "OrderPriority",
    # Operation
    "Operation",
    "OperationStatus",
    # Offer
    "Offer",
    "OfferStatus",
    # Document
    "Document",
    "DocumentCategory",
    # Inbox
    "InboxMessage",
    "InboxClassification",
    "InboxStatus",
    "MessageDirection",
    # EmailAttachment
    "EmailAttachment",
    "OCRStatus",
    # DrawingAnalysis
    "DrawingAnalysis",
    # ProcessingTask
    "ProcessingTask",
    "ProcessingStage",
    "ProcessingStatus",
    # DeadLetterEntry
    "DeadLetterEntry",
    # MaterialPrice
    "MaterialPrice",
    # Notification
    "Notification",
    "NotificationType",
    # OrderEmbedding
    "OrderEmbedding",
    # Audit
    "AuditLog",
    "AuditAction",
    # Pohoda Sync
    "PohodaSyncLog",
    "SyncDirection",
    "SyncStatus",
    # User
    "User",
    "UserRole",
    # Gamification
    "UserPoints",
    "PointsAction",
    "PointsPeriod",
    # Subcontractor
    "Subcontractor",
    "Subcontract",
    "SubcontractStatus",
    # F3 models
    "CalculationFeedback",
    "CorrectionType",
    "ClassificationFeedback",
    "DocumentEmbedding",
]
