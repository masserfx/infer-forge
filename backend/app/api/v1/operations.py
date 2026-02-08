"""API endpoints for operations (výrobní operace)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.user import User, UserRole
from app.schemas.operation import (
    OperationCreate,
    OperationListResponse,
    OperationReorderRequest,
    OperationResponse,
    OperationUpdate,
)
from app.services.operation import OperationService

router = APIRouter(tags=["operations"])


def get_operation_service(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
) -> OperationService:
    """Dependency to get OperationService with current user context."""
    return OperationService(db=db, user_id=current_user.id)


@router.get(
    "/zakazky/{order_id}/operace",
    response_model=OperationListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_operations(
    order_id: UUID,
    service: OperationService = Depends(get_operation_service),
) -> OperationListResponse:
    """Get all operations for an order.

    Args:
        order_id: Order ID
        service: Operation service

    Returns:
        List of operations sorted by sequence
    """
    operations = await service.get_by_order(order_id)
    items = [OperationResponse.model_validate(op) for op in operations]
    return OperationListResponse(items=items, total=len(items))


@router.post(
    "/zakazky/{order_id}/operace",
    response_model=OperationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_role(UserRole.VEDENI, UserRole.TECHNOLOG))
    ],
)
async def create_operation(
    order_id: UUID,
    data: OperationCreate,
    service: OperationService = Depends(get_operation_service),
) -> OperationResponse:
    """Create a new operation for an order.

    Requires VEDENI, TECHNOLOG, or VYROBNI role.

    Args:
        order_id: Order ID
        data: Operation creation data
        service: Operation service

    Returns:
        Created operation

    Raises:
        HTTPException: 404 if order not found
    """
    operation = await service.create(order_id, data)
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )
    return OperationResponse.model_validate(operation)


@router.put(
    "/zakazky/{order_id}/operace/{operation_id}",
    response_model=OperationResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(require_role(UserRole.VEDENI, UserRole.TECHNOLOG))
    ],
)
async def update_operation(
    order_id: UUID,
    operation_id: UUID,
    data: OperationUpdate,
    service: OperationService = Depends(get_operation_service),
) -> OperationResponse:
    """Update an operation.

    Requires VEDENI, TECHNOLOG, or VYROBNI role.

    Args:
        order_id: Order ID (for URL consistency, not validated)
        operation_id: Operation ID
        data: Update data
        service: Operation service

    Returns:
        Updated operation

    Raises:
        HTTPException: 404 if operation not found
    """
    operation = await service.update(operation_id, data)
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operation {operation_id} not found",
        )
    return OperationResponse.model_validate(operation)


@router.delete(
    "/zakazky/{order_id}/operace/{operation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.VEDENI))],
)
async def delete_operation(
    order_id: UUID,
    operation_id: UUID,
    service: OperationService = Depends(get_operation_service),
) -> None:
    """Delete an operation.

    Requires VEDENI role.

    Args:
        order_id: Order ID (for URL consistency, not validated)
        operation_id: Operation ID
        service: Operation service

    Raises:
        HTTPException: 404 if operation not found
    """
    deleted = await service.delete(operation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operation {operation_id} not found",
        )


@router.post(
    "/zakazky/{order_id}/operace/reorder",
    response_model=OperationListResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(require_role(UserRole.VEDENI, UserRole.TECHNOLOG))
    ],
)
async def reorder_operations(
    order_id: UUID,
    data: OperationReorderRequest,
    service: OperationService = Depends(get_operation_service),
) -> OperationListResponse:
    """Reorder operations by updating sequence numbers.

    Requires VEDENI, TECHNOLOG, or VYROBNI role.

    Args:
        order_id: Order ID
        data: List of operation IDs in new order
        service: Operation service

    Returns:
        List of operations with updated sequences

    Raises:
        HTTPException: 400 if operation IDs don't match order's operations
    """
    try:
        operations = await service.reorder(order_id, data.operation_ids)
        items = [OperationResponse.model_validate(op) for op in operations]
        return OperationListResponse(items=items, total=len(items))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
