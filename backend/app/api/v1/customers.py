"""Customer API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_role
from app.models.user import User, UserRole
from app.schemas import CustomerCreate, CustomerResponse, CustomerUpdate
from app.services import CustomerService

router = APIRouter(prefix="/zakaznici", tags=["Zákazníci"])


@router.get("/", response_model=list[CustomerResponse])
async def get_customers(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of records"),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CustomerResponse]:
    """Get all customers with pagination."""
    service = CustomerService(db)
    customers = await service.get_all(skip=skip, limit=limit)
    return [CustomerResponse.model_validate(c) for c in customers]


@router.post(
    "/",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_customer(
    customer_data: CustomerCreate,
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """Create a new customer."""
    service = CustomerService(db)
    try:
        customer = await service.create(customer_data)
        await db.commit()
        return CustomerResponse.model_validate(customer)
    except Exception as e:
        await db.rollback()
        if "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Customer with IČO {customer_data.ico} already exists",
            ) from e
        raise


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """Get customer by ID."""
    service = CustomerService(db)
    customer = await service.get_by_id(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found",
        )
    return CustomerResponse.model_validate(customer)


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: UUID,
    customer_data: CustomerUpdate,
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """Update customer."""
    service = CustomerService(db)
    customer = await service.update(customer_id, customer_data)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found",
        )
    await db.commit()
    return CustomerResponse.model_validate(customer)
