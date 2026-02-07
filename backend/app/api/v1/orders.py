"""Order API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models import OrderStatus
from app.schemas import OrderCreate, OrderResponse, OrderStatusUpdate, OrderUpdate
from app.services import OrderService

router = APIRouter(prefix="/zakazky", tags=["Zakázky"])


@router.get("/", response_model=list[OrderResponse])
async def get_orders(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of records"),
    status: Optional[OrderStatus] = Query(default=None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
) -> list[OrderResponse]:
    """Get all orders with pagination and optional filtering.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Optional status filter
        db: Database session

    Returns:
        List of orders
    """
    service = OrderService(db)
    orders = await service.get_all(skip=skip, limit=limit, status=status)
    return [OrderResponse.model_validate(o) for o in orders]


@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Create a new order with items.

    Args:
        order_data: Order creation data
        db: Database session

    Returns:
        Created order

    Raises:
        HTTPException: If order number already exists or validation fails
    """
    service = OrderService(db)
    try:
        order = await service.create(order_data)
        await db.commit()
        return OrderResponse.model_validate(order)
    except Exception as e:
        await db.rollback()
        if "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Order with number {order_data.number} already exists",
            )
        raise


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Get order by ID.

    Args:
        order_id: Order UUID
        db: Database session

    Returns:
        Order details with items and customer

    Raises:
        HTTPException: If order not found
    """
    service = OrderService(db)
    order = await service.get_by_id(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )
    return OrderResponse.model_validate(order)


@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: UUID,
    order_data: OrderUpdate,
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Update order.

    Args:
        order_id: Order UUID
        order_data: Order update data
        db: Database session

    Returns:
        Updated order

    Raises:
        HTTPException: If order not found
    """
    service = OrderService(db)
    order = await service.update(order_id, order_data)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )
    await db.commit()
    return OrderResponse.model_validate(order)


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: UUID,
    status_data: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Update order status with validation.

    Args:
        order_id: Order UUID
        status_data: New status
        db: Database session

    Returns:
        Updated order

    Raises:
        HTTPException: If order not found or status transition is invalid
    """
    service = OrderService(db)
    try:
        order = await service.change_status(order_id, status_data.status)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order {order_id} not found",
            )
        await db.commit()
        return OrderResponse.model_validate(order)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
