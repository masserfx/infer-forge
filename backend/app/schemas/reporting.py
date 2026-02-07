"""Reporting Pydantic schemas for analytics and dashboards."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class StatusCount(BaseModel):
    """Count of entities per status."""

    status: str
    count: int
    label: str


class PipelineReport(BaseModel):
    """Order pipeline breakdown by status."""

    statuses: list[StatusCount] = Field(default_factory=list)
    total_orders: int = 0


class RevenueItem(BaseModel):
    """Revenue data for a period."""

    period: str  # e.g. "2026-01" or "2026-Q1"
    total_calculations: Decimal = Decimal("0")
    total_offers: Decimal = Decimal("0")
    offers_count: int = 0
    calculations_count: int = 0


class RevenueReport(BaseModel):
    """Revenue overview."""

    total_calculation_value: Decimal = Decimal("0")
    total_offer_value: Decimal = Decimal("0")
    approved_calculations: int = 0
    pending_offers: int = 0
    accepted_offers: int = 0
    monthly: list[RevenueItem] = Field(default_factory=list)


class ProductionItem(BaseModel):
    """Order in production with deadline info."""

    order_id: str
    order_number: str
    customer_name: str
    status: str
    priority: str
    due_date: date | None = None
    days_until_due: int | None = None
    items_count: int = 0


class ProductionReport(BaseModel):
    """Production overview."""

    in_production: int = 0
    in_expedition: int = 0
    overdue: int = 0
    due_this_week: int = 0
    due_this_month: int = 0
    orders: list[ProductionItem] = Field(default_factory=list)


class CustomerStats(BaseModel):
    """Customer statistics."""

    customer_id: str
    company_name: str
    ico: str
    orders_count: int = 0
    total_value: Decimal = Decimal("0")
    active_orders: int = 0


class CustomerReport(BaseModel):
    """Customer analytics."""

    total_customers: int = 0
    active_customers: int = 0
    top_customers: list[CustomerStats] = Field(default_factory=list)


class DashboardStats(BaseModel):
    """Aggregated dashboard statistics."""

    total_orders: int = 0
    orders_in_production: int = 0
    new_inbox_messages: int = 0
    pending_invoicing: int = 0
    total_documents: int = 0
    total_calculations: int = 0
    total_revenue: Decimal = Decimal("0")
    overdue_orders: int = 0
    pipeline: PipelineReport = Field(default_factory=PipelineReport)
