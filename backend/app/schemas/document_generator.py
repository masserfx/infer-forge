"""Pydantic schemas for document generation."""

from pydantic import BaseModel


class GenerateOfferRequest(BaseModel):
    """Optional overrides for offer generation."""

    valid_days: int = 30
    note: str | None = None


class GenerateProductionSheetRequest(BaseModel):
    """Optional overrides for production sheet generation."""

    include_controls: bool = True
    note: str | None = None


class GenerateInvoiceRequest(BaseModel):
    """Request for invoice PDF generation."""

    invoice_type: str = "final"  # "final", "advance", "proforma"
    due_days: int = 14
    note: str | None = None


class GenerateDeliveryNoteRequest(BaseModel):
    """Request for delivery note PDF generation."""

    delivery_address: str | None = None
    note: str | None = None


class GenerateOrderConfirmationRequest(BaseModel):
    """Request for order confirmation PDF generation."""

    show_prices: bool = False
    delivery_terms: str | None = None
    payment_terms: str | None = None
    note: str | None = None
