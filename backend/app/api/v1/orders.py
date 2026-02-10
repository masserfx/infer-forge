"""Order API endpoints."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models import Offer, Order, OrderStatus
from app.models.document import Document
from app.models.inbox import InboxMessage, MessageDirection
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
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI, UserRole.UCETNI)),
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
    order_ids: list[UUID] = Field(..., max_length=100)
    status: OrderStatus


class BulkAssignUpdate(BaseModel):
    order_ids: list[UUID] = Field(..., max_length=100)
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
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI, UserRole.UCETNI)),
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


@router.get("/{order_id}/nabidky")
async def get_order_offers(
    order_id: UUID,
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of records"),
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI, UserRole.UCETNI)),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get all offers for an order."""
    result = await db.execute(
        select(Offer).where(Offer.order_id == order_id).order_by(Offer.created_at.desc()).offset(skip).limit(limit)
    )
    offers = result.scalars().all()
    return [
        {
            "id": str(o.id),
            "number": o.number,
            "total_price": str(o.total_price),
            "valid_until": str(o.valid_until),
            "status": o.status.value,
            "created_at": o.created_at.isoformat(),
        }
        for o in offers
    ]


@router.get("/{order_id}/emails")
async def get_order_emails(
    order_id: UUID,
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of records"),
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI, UserRole.UCETNI)),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get all emails associated with an order (inbound + outbound), chronologically.

    Outbound offer emails are enriched with offer_id, offer_number, and document_id
    for the attached PDF.
    """
    result = await db.execute(
        select(InboxMessage)
        .where(InboxMessage.order_id == order_id)
        .order_by(InboxMessage.received_at.asc())
        .offset(skip)
        .limit(limit)
    )
    messages = result.scalars().all()

    # Pre-load offers and their documents for this order
    offer_result = await db.execute(
        select(Offer).where(Offer.order_id == order_id)
    )
    offers = {str(o.id): o for o in offer_result.scalars().all()}

    doc_result = await db.execute(
        select(Document).where(
            Document.entity_type == "offer",
            Document.entity_id.in_([o.id for o in offers.values()]) if offers else False,
        )
    )
    # Map offer_id → document
    offer_docs: dict[str, Document] = {}
    for doc in doc_result.scalars().all():
        offer_docs[str(doc.entity_id)] = doc

    items = []
    for m in messages:
        item: dict = {
            "id": str(m.id),
            "from_email": m.from_email,
            "subject": m.subject,
            "body_text": m.body_text or "",
            "received_at": m.received_at.isoformat(),
            "classification": m.classification.value if m.classification else None,
            "direction": m.direction.value if hasattr(m, "direction") and m.direction else "inbound",
            "status": m.status.value,
        }

        # Enrich outbound offer emails with offer + document info
        if (
            hasattr(m, "direction")
            and m.direction == MessageDirection.OUTBOUND
            and m.message_id
            and m.message_id.startswith("offer-")
        ):
            # Extract offer_id from message_id "offer-{uuid}@infer.cz"
            offer_id_str = m.message_id.replace("offer-", "").replace("@infer.cz", "")
            if offer_id_str in offers:
                offer = offers[offer_id_str]
                item["offer_id"] = str(offer.id)
                item["offer_number"] = offer.number
                item["offer_status"] = offer.status.value
                doc = offer_docs.get(offer_id_str)
                if doc:
                    item["document_id"] = str(doc.id)
                    item["document_name"] = doc.file_name

        items.append(item)

    return items


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
