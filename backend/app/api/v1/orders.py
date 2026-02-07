"""Order API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_role
from app.models import OrderStatus
from app.models.user import User, UserRole
from app.schemas import OrderCreate, OrderResponse, OrderStatusUpdate, OrderUpdate
from app.services import OrderService

router = APIRouter(prefix="/zakazky", tags=["Zakázky"])


@router.get("/", response_model=list[OrderResponse])
async def get_orders(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of records"),
    status: OrderStatus | None = Query(default=None, description="Filter by status"),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OrderResponse]:
    """Get all orders with pagination and optional filtering."""
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
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Create a new order with items."""
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
            ) from e
        raise


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Get order by ID."""
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
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Update order."""
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
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Update order status with validation."""
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
        ) from e
