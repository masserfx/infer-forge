"""Inbox Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import InboxClassification, InboxStatus


class InboxMessageResponse(BaseModel):
    """Schema for inbox message responses."""

    id: UUID
    message_id: str = Field(..., description="Email message ID")
    from_email: EmailStr = Field(..., description="Sender email address")
    subject: str = Field(..., description="Email subject")
    body_text: str = Field(..., description="Email body text")
    received_at: datetime = Field(..., description="Email received timestamp")
    classification: InboxClassification | None = Field(None, description="AI classification")
    confidence: float | None = Field(
        None, ge=0, le=1, description="Classification confidence score"
    )
    status: InboxStatus = Field(..., description="Processing status")
    customer_id: UUID | None = Field(None, description="Assigned customer ID")
    order_id: UUID | None = Field(None, description="Assigned order ID")
    auto_reply_sent: bool = Field(False, description="Whether auto-reply was sent")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InboxAssign(BaseModel):
    """Schema for assigning inbox message to customer/order."""

    customer_id: UUID | None = Field(None, description="Customer to assign")
    order_id: UUID | None = Field(None, description="Order to assign")


class InboxReclassify(BaseModel):
    """Schema for reclassifying inbox message."""

    classification: InboxClassification = Field(..., description="New classification")
