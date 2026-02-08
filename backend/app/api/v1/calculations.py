"""Calculation API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
    offer_number: str = Query(..., description="Offer number"),
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
