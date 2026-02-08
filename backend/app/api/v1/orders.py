"""Order API endpoints."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models import Order, OrderStatus
from app.models.user import User, UserRole
from app.schemas import OrderCreate, OrderResponse, OrderStatusUpdate, OrderUpdate
from app.schemas.embedding import SimilarOrderResult, SimilarOrdersResponse, SimilarSearchRequest
from app.services import EmbeddingService, OrderService

router = APIRouter(prefix="/zakazky", tags=["Zakázky"])


def _order_response(order: Order) -> OrderResponse:
    """Convert Order model to OrderResponse with assigned_to_name."""
    resp = OrderResponse.model_validate(order)
    if order.assignee:
        resp.assigned_to_name = order.assignee.full_name
    return resp


@router.get("", response_model=list[OrderResponse])
async def get_orders(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of records"),
    status: OrderStatus | None = Query(default=None, description="Filter by status"),
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> list[OrderResponse]:
    """Get all orders with pagination and optional filtering."""
    service = OrderService(db)
    orders = await service.get_all(skip=skip, limit=limit, status=status)
    return [_order_response(o) for o in orders]


@router.post(
    "",
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
        return _order_response(order)
    except Exception as e:
        await db.rollback()
        if "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Order with number {order_data.number} already exists",
            ) from e
        raise


class BulkStatusUpdate(BaseModel):
    order_ids: list[UUID]
    status: OrderStatus


class BulkAssignUpdate(BaseModel):
    order_ids: list[UUID]
    assignee_id: UUID


@router.post("/bulk/status")
async def bulk_update_status(
    data: BulkStatusUpdate,
    user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Bulk update order statuses."""
    service = OrderService(db, user_id=user.id)
    updated = 0
    errors = []
    for order_id in data.order_ids:
        try:
            result = await service.change_status(order_id, data.status)
            if result:
                updated += 1
            else:
                errors.append(f"{order_id}: not found")
        except ValueError as e:
            errors.append(f"{order_id}: {str(e)}")
    await db.commit()
    return {"updated": updated, "errors": errors}


@router.post("/bulk/assign")
async def bulk_assign_orders(
    data: BulkAssignUpdate,
    user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Bulk assign orders to a user."""
    service = OrderService(db, user_id=user.id)
    updated = 0
    errors = []
    for order_id in data.order_ids:
        try:
            result = await service.assign_order(order_id, data.assignee_id)
            if result:
                updated += 1
            else:
                errors.append(f"{order_id}: not found")
        except Exception as e:
            errors.append(f"{order_id}: {str(e)}")
    await db.commit()
    return {"updated": updated, "errors": errors}


@router.get("/next-number")
async def get_next_order_number(
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the next order number based on sequential pattern."""
    year = datetime.now(UTC).year
    prefix = f"ZAK-{year}-"
    result = await db.execute(
        select(func.count()).select_from(Order).where(Order.number.like(f"{prefix}%"))
    )
    count = (result.scalar() or 0) + 1
    return {"next_number": f"{prefix}{count:04d}"}


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
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
    return _order_response(order)


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
    return _order_response(order)


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
        return _order_response(order)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.patch("/{order_id}/assign", response_model=OrderResponse)
async def assign_order(
    order_id: UUID,
    user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Assign order to the current user (claim order)."""
    service = OrderService(db, user_id=user.id)
    order = await service.assign_order(order_id, user.id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )
    await db.commit()
    return _order_response(order)


@router.get("/{order_id}/similar", response_model=SimilarOrdersResponse)
async def get_similar_orders(
    order_id: UUID,
    limit: int = Query(default=5, ge=1, le=20, description="Max similar orders"),
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> SimilarOrdersResponse:
    """Find similar orders using vector similarity search."""
    service = EmbeddingService(db)
    similar = await service.find_similar(order_id, limit=limit)
    return SimilarOrdersResponse(
        order_id=str(order_id),
        similar_orders=similar,
        total=len(similar),
    )


@router.post("/search/similar", response_model=list[SimilarOrderResult])
async def search_similar_orders(
    request: SimilarSearchRequest,
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> list[SimilarOrderResult]:
    """Search orders by text similarity."""
    service = EmbeddingService(db)
    return await service.search_by_text(request.query, limit=request.limit)


@router.get("/{order_id}/predict-due-date")
async def predict_due_date(
    order_id: UUID,
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get AI-predicted completion time for an order."""
    from app.services.prediction import PredictionService
    service = PredictionService(db)
    return await service.predict_due_date(order_id)


@router.get("/{order_id}/suggest-assignee")
async def suggest_assignee(
    order_id: UUID,
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get AI suggestion for order assignee."""
    from app.services.assignment import AssignmentService
    service = AssignmentService(db)
    return await service.suggest_assignee(order_id)


@router.post(
    "/from-offer/{offer_id}",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_order_from_offer(
    offer_id: UUID,
    user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Convert an accepted offer to a new order.

    Creates a new order in OBJEDNAVKA status from an accepted offer,
    copying all items from the source order.
    """
    service = OrderService(db, user_id=user.id)
    try:
        order = await service.convert_offer_to_order(offer_id)
        await db.commit()
        return _order_response(order)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to convert offer: {str(e)}",
        ) from e
