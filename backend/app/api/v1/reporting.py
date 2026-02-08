"""Reporting API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.integrations.excel.exporter import ExcelExporter
from app.models.user import User, UserRole
from app.schemas import (
    CustomerReport,
    DashboardStats,
    MaterialRequirementsResponse,
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


@router.get("/material-requirements")
async def get_material_requirements(
    order_ids: list[UUID] | None = Query(default=None, description="Filter by specific order IDs"),  # noqa: E501
    status_filter: list[str] | None = Query(default=None, description="Filter by order status"),
    response_format: str = Query(default="json", pattern="^(json|excel)$", description="Response format: json or excel", alias="format"),  # noqa: E501
    user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> MaterialRequirementsResponse | StreamingResponse:
    """Get aggregated material requirements (BOM / nákupní seznam).

    Returns JSON response or Excel file depending on format parameter.
    Accessible by TECHNOLOG and VEDENI roles.
    """
    service = ReportingService(db)
    result = await service.get_material_requirements(
        order_ids=order_ids,
        status_filter=status_filter,
    )

    if response_format == "excel":
        # Convert to dict for Excel export
        items_dict = [item.model_dump() for item in result.items]

        exporter = ExcelExporter()
        excel_bytes = await exporter.export_material_requirements(
            items=items_dict,
            total_estimated_cost=result.total_estimated_cost,
            order_count=result.order_count,
        )

        return StreamingResponse(
            iter([excel_bytes]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=materialova_potreba.xlsx"
            },
        )

    return result
