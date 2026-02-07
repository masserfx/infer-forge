"""Customer API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas import CustomerCreate, CustomerResponse, CustomerUpdate
from app.services import CustomerService

router = APIRouter(prefix="/zakaznici", tags=["Zákazníci"])


@router.get("/", response_model=list[CustomerResponse])
async def get_customers(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of records"),
    db: AsyncSession = Depends(get_db),
) -> list[CustomerResponse]:
    """Get all customers with pagination.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of customers
    """
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
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """Create a new customer.

    Args:
        customer_data: Customer creation data
        db: Database session

    Returns:
        Created customer

    Raises:
        HTTPException: If customer with same IČO already exists
    """
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
            )
        raise


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """Get customer by ID.

    Args:
        customer_id: Customer UUID
        db: Database session

    Returns:
        Customer details

    Raises:
        HTTPException: If customer not found
    """
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
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """Update customer.

    Args:
        customer_id: Customer UUID
        customer_data: Customer update data
        db: Database session

    Returns:
        Updated customer

    Raises:
        HTTPException: If customer not found
    """
    service = CustomerService(db)
    customer = await service.update(customer_id, customer_data)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found",
        )
    await db.commit()
    return CustomerResponse.model_validate(customer)
