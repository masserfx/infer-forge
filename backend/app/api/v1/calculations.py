"""Calculation API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models import CalculationStatus
from app.models.user import User, UserRole
from app.schemas import (
    CalculationCreate,
    CalculationItemCreate,
    CalculationItemUpdate,
    CalculationResponse,
    CalculationUpdate,
)
from app.services import CalculationService

router = APIRouter(prefix="/kalkulace", tags=["Kalkulace"])


@router.post(
    "",
    response_model=CalculationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_calculation(
    data: CalculationCreate,
    _user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> CalculationResponse:
    """Create a new calculation for an order."""
    service = CalculationService(db)
    try:
        calculation = await service.create(data)
        await db.commit()
        return CalculationResponse.model_validate(calculation)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/ai-estimate/{order_id}")
async def ai_estimate(
    order_id: UUID,
    _user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get AI cost estimation for an order's items.

    Uses CalculationAgent to estimate material costs, labor hours,
    overhead and margin based on order items.
    """
    from app.core.config import get_settings
    settings = get_settings()

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Anthropic API key not configured. Set ANTHROPIC_API_KEY.",
        )

    # Load order with items
    from app.services import OrderService
    order_service = OrderService(db)
    order = await order_service.get_by_id(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )

    # Build items list for agent
    items = []
    for item in order.items:
        items.append({
            "name": item.name,
            "material": item.material or "Nespecifikováno",
            "dimension": f"DN{item.dn}" if item.dn else "",
            "quantity": item.quantity,
            "unit": item.unit,
        })

    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order has no items to estimate",
        )

    # Run estimation
    from app.agents.calculation_agent import CalculationAgent
    agent = CalculationAgent(
        api_key=settings.ANTHROPIC_API_KEY,
        db_session=db,
    )

    description = f"Zakázka {order.number}"
    if order.note:
        description += f" - {order.note}"

    estimate = await agent.estimate(description=description, items=items)

    return {
        "order_id": str(order_id),
        "order_number": order.number,
        "material_cost_czk": estimate.material_cost_czk,
        "labor_hours": estimate.labor_hours,
        "labor_cost_czk": estimate.labor_cost_czk,
        "overhead_czk": estimate.overhead_czk,
        "margin_percent": estimate.margin_percent,
        "total_czk": estimate.total_czk,
        "reasoning": estimate.reasoning,
        "items": [
            {
                "name": item.name,
                "material_cost_czk": item.material_cost_czk,
                "labor_hours": item.labor_hours,
                "notes": item.notes,
            }
            for item in estimate.breakdown
        ],
    }


@router.get("", response_model=list[CalculationResponse])
async def list_calculations(
    status_filter: CalculationStatus | None = Query(
        None, alias="status", description="Filter by status"
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    _user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> list[CalculationResponse]:
    """List all calculations with optional status filter."""
    service = CalculationService(db)
    calculations = await service.get_all(
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    return [CalculationResponse.model_validate(c) for c in calculations]


@router.get("/{calculation_id}", response_model=CalculationResponse)
async def get_calculation(
    calculation_id: UUID,
    _user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> CalculationResponse:
    """Get calculation by ID with all items."""
    service = CalculationService(db)
    calculation = await service.get_by_id(calculation_id)
    if not calculation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calculation {calculation_id} not found",
        )
    return CalculationResponse.model_validate(calculation)


@router.get("/zakazka/{order_id}", response_model=list[CalculationResponse])
async def get_order_calculations(
    order_id: UUID,
    _user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> list[CalculationResponse]:
    """Get all calculations for an order."""
    service = CalculationService(db)
    calculations = await service.get_by_order(order_id)
    return [CalculationResponse.model_validate(c) for c in calculations]


@router.put("/{calculation_id}", response_model=CalculationResponse)
async def update_calculation(
    calculation_id: UUID,
    data: CalculationUpdate,
    _user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> CalculationResponse:
    """Update calculation metadata (name, note, margin, status)."""
    service = CalculationService(db)
    calculation = await service.update(calculation_id, data)
    if not calculation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calculation {calculation_id} not found",
        )
    await db.commit()
    return CalculationResponse.model_validate(calculation)


@router.delete("/{calculation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calculation(
    calculation_id: UUID,
    _user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a calculation."""
    service = CalculationService(db)
    deleted = await service.delete(calculation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calculation {calculation_id} not found",
        )
    await db.commit()


# --- Items ---


@router.post(
    "/{calculation_id}/polozky",
    response_model=CalculationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_calculation_item(
    calculation_id: UUID,
    item_data: CalculationItemCreate,
    _user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> CalculationResponse:
    """Add an item to a calculation."""
    service = CalculationService(db)
    calculation = await service.add_item(calculation_id, item_data)
    if not calculation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calculation {calculation_id} not found",
        )
    await db.commit()
    return CalculationResponse.model_validate(calculation)


@router.put(
    "/{calculation_id}/polozky/{item_id}",
    response_model=CalculationResponse,
)
async def update_calculation_item(
    calculation_id: UUID,
    item_id: UUID,
    item_data: CalculationItemUpdate,
    _user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> CalculationResponse:
    """Update a calculation item."""
    service = CalculationService(db)
    calculation = await service.update_item(calculation_id, item_id, item_data)
    if not calculation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calculation {calculation_id} or item {item_id} not found",
        )
    await db.commit()
    return CalculationResponse.model_validate(calculation)


@router.delete(
    "/{calculation_id}/polozky/{item_id}",
    response_model=CalculationResponse,
)
async def remove_calculation_item(
    calculation_id: UUID,
    item_id: UUID,
    _user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> CalculationResponse:
    """Remove an item from a calculation."""
    service = CalculationService(db)
    calculation = await service.remove_item(calculation_id, item_id)
    if not calculation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calculation {calculation_id} or item {item_id} not found",
        )
    await db.commit()
    return CalculationResponse.model_validate(calculation)


# --- Offer generation ---


@router.post(
    "/{calculation_id}/nabidka",
    status_code=status.HTTP_201_CREATED,
)
async def generate_offer(
    calculation_id: UUID,
    offer_number: str | None = Query(default=None, description="Offer number (auto-generated if empty)"),
    valid_days: int = Query(default=30, ge=1, le=365, description="Offer validity in days"),
    _user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate an Offer from a calculation."""
    service = CalculationService(db)
    try:
        offer = await service.generate_offer(calculation_id, offer_number, valid_days)
        if not offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Calculation {calculation_id} not found",
            )
        await db.commit()
        return {
            "offer_id": str(offer.id),
            "number": offer.number,
            "total_price": str(offer.total_price),
            "valid_until": str(offer.valid_until),
        }
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


class CalculationFeedbackRequest(BaseModel):
    """Request body for calculation feedback."""

    original_items: list[dict] = Field(default_factory=list)
    corrected_items: list[dict] = Field(default_factory=list)
    correction_type: str = Field(default="price")


@router.post("/{calculation_id}/feedback")
async def submit_calculation_feedback(
    calculation_id: UUID,
    feedback: CalculationFeedbackRequest,
    user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Submit feedback on AI calculation for learning loop."""
    import json
    from app.models.calculation_feedback import CalculationFeedback, CorrectionType

    fb = CalculationFeedback(
        calculation_id=calculation_id,
        original_items=json.dumps(feedback.original_items),
        corrected_items=json.dumps(feedback.corrected_items),
        correction_type=CorrectionType(feedback.correction_type),
        user_id=user.id,
    )
    db.add(fb)
    await db.commit()
    return {"id": str(fb.id), "status": "saved"}


@router.get("/{calculation_id}/anomalies")
async def get_calculation_anomalies(
    calculation_id: UUID,
    _user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check calculation for anomalies compared to historical data."""
    from app.services.anomaly import AnomalyService
    service = AnomalyService(db)
    anomalies = await service.check_calculation(calculation_id)
    return {"calculation_id": str(calculation_id), "anomalies": anomalies}
