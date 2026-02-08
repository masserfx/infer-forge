"""Subcontractor and Subcontract API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.user import User, UserRole
from app.schemas.subcontractor import (
    SubcontractCreate,
    SubcontractListResponse,
    SubcontractorCreate,
    SubcontractorListResponse,
    SubcontractorResponse,
    SubcontractorUpdate,
    SubcontractResponse,
    SubcontractUpdate,
)
from app.services.subcontractor import SubcontractorService

router = APIRouter(prefix="/subdodavatele", tags=["Subdodavatelé"])


# --- Subcontractor endpoints ---


@router.get("", response_model=SubcontractorListResponse)
async def get_subcontractors(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of records"),
    is_active: bool | None = Query(default=None, description="Filter by active status"),
    specialization: str | None = Query(
        default=None, description="Filter by specialization (partial match)"
    ),
    _user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> SubcontractorListResponse:
    """Get all subcontractors with pagination and filters."""
    service = SubcontractorService(db)
    subcontractors, total = await service.get_all_subcontractors(
        skip=skip, limit=limit, is_active=is_active, specialization=specialization
    )
    return SubcontractorListResponse(
        items=[SubcontractorResponse.model_validate(s) for s in subcontractors],
        total=total,
    )


@router.post(
    "",
    response_model=SubcontractorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_subcontractor(
    subcontractor_data: SubcontractorCreate,
    user: User = Depends(require_role(UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> SubcontractorResponse:
    """Create a new subcontractor."""
    service = SubcontractorService(db, user_id=user.id)
    try:
        subcontractor = await service.create_subcontractor(subcontractor_data)
        await db.commit()
        return SubcontractorResponse.model_validate(subcontractor)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subcontractor: {str(e)}",
        ) from e


@router.get("/{subcontractor_id}", response_model=SubcontractorResponse)
async def get_subcontractor(
    subcontractor_id: UUID,
    _user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> SubcontractorResponse:
    """Get subcontractor by ID."""
    service = SubcontractorService(db)
    subcontractor = await service.get_subcontractor_by_id(subcontractor_id)
    if not subcontractor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subcontractor {subcontractor_id} not found",
        )
    return SubcontractorResponse.model_validate(subcontractor)


@router.put("/{subcontractor_id}", response_model=SubcontractorResponse)
async def update_subcontractor(
    subcontractor_id: UUID,
    subcontractor_data: SubcontractorUpdate,
    user: User = Depends(require_role(UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> SubcontractorResponse:
    """Update subcontractor."""
    service = SubcontractorService(db, user_id=user.id)
    subcontractor = await service.update_subcontractor(subcontractor_id, subcontractor_data)
    if not subcontractor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subcontractor {subcontractor_id} not found",
        )
    await db.commit()
    return SubcontractorResponse.model_validate(subcontractor)


@router.delete("/{subcontractor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subcontractor(
    subcontractor_id: UUID,
    user: User = Depends(require_role(UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete subcontractor."""
    service = SubcontractorService(db, user_id=user.id)
    deleted = await service.delete_subcontractor(subcontractor_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subcontractor {subcontractor_id} not found",
        )
    await db.commit()


# --- Subcontract endpoints ---


@router.get("/zakazky/{order_id}/kooperace", response_model=SubcontractListResponse)
async def get_order_subcontracts(
    order_id: UUID,
    _user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> SubcontractListResponse:
    """Get all subcontracts for an order."""
    service = SubcontractorService(db)
    subcontracts = await service.get_subcontracts_by_order(order_id)
    return SubcontractListResponse(
        items=[SubcontractResponse.model_validate(s) for s in subcontracts],
        total=len(subcontracts),
    )


@router.post(
    "/zakazky/{order_id}/kooperace",
    response_model=SubcontractResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_order_subcontract(
    order_id: UUID,
    subcontract_data: SubcontractCreate,
    user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> SubcontractResponse:
    """Create a new subcontract for an order."""
    service = SubcontractorService(db, user_id=user.id)
    try:
        subcontract = await service.create_subcontract(order_id, subcontract_data)
        await db.commit()
        return SubcontractResponse.model_validate(subcontract)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subcontract: {str(e)}",
        ) from e


@router.put(
    "/zakazky/{order_id}/kooperace/{subcontract_id}",
    response_model=SubcontractResponse,
)
async def update_order_subcontract(
    order_id: UUID,
    subcontract_id: UUID,
    subcontract_data: SubcontractUpdate,
    user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> SubcontractResponse:
    """Update a subcontract."""
    service = SubcontractorService(db, user_id=user.id)
    subcontract = await service.update_subcontract(subcontract_id, subcontract_data)
    if not subcontract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subcontract {subcontract_id} not found",
        )
    if subcontract.order_id != order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Subcontract {subcontract_id} does not belong to order {order_id}",
        )
    await db.commit()
    return SubcontractResponse.model_validate(subcontract)


@router.delete(
    "/zakazky/{order_id}/kooperace/{subcontract_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_order_subcontract(
    order_id: UUID,
    subcontract_id: UUID,
    user: User = Depends(require_role(UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a subcontract."""
    service = SubcontractorService(db, user_id=user.id)
    subcontract = await service.get_subcontract_by_id(subcontract_id)
    if not subcontract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subcontract {subcontract_id} not found",
        )
    if subcontract.order_id != order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Subcontract {subcontract_id} does not belong to order {order_id}",
        )

    deleted = await service.delete_subcontract(subcontract_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subcontract {subcontract_id} not found",
        )
    await db.commit()
