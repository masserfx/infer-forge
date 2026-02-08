"""Reporting API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.user import User, UserRole
from app.schemas import (
    CustomerReport,
    DashboardStats,
    PipelineReport,
    ProductionReport,
    RevenueReport,
)
from app.services import ReportingService

router = APIRouter(prefix="/reporting", tags=["Reporting"])


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    _user: User = Depends(require_role(UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> DashboardStats:
    """Get aggregated dashboard statistics."""
    service = ReportingService(db)
    return await service.get_dashboard_stats()


@router.get("/pipeline", response_model=PipelineReport)
async def get_pipeline_report(
    _user: User = Depends(require_role(UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> PipelineReport:
    """Get order pipeline breakdown by status."""
    service = ReportingService(db)
    return await service.get_pipeline_report()


@router.get("/revenue", response_model=RevenueReport)
async def get_revenue_report(
    months: int = Query(default=12, ge=1, le=60, description="Number of months to include"),
    _user: User = Depends(require_role(UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> RevenueReport:
    """Get revenue report with monthly breakdown."""
    service = ReportingService(db)
    return await service.get_revenue_report(months=months)


@router.get("/production", response_model=ProductionReport)
async def get_production_report(
    _user: User = Depends(require_role(UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> ProductionReport:
    """Get production overview with deadline tracking."""
    service = ReportingService(db)
    return await service.get_production_report()


@router.get("/customers", response_model=CustomerReport)
async def get_customer_report(
    limit: int = Query(default=20, ge=1, le=100, description="Number of top customers"),
    _user: User = Depends(require_role(UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> CustomerReport:
    """Get customer analytics."""
    service = ReportingService(db)
    return await service.get_customer_report(limit=limit)
