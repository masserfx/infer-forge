"""Pohoda integration API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.pohoda_sync import SyncStatus
from app.schemas.pohoda import (
    PohodaSyncLogResponse,
    PohodaSyncRequest,
    PohodaSyncResult,
    PohodaSyncStatusResponse,
)
from app.services.pohoda import PohodaService

router = APIRouter(prefix="/pohoda", tags=["Pohoda"])


@router.post(
    "/sync",
    response_model=PohodaSyncResult,
    status_code=status.HTTP_200_OK,
)
async def sync_entity(
    request: PohodaSyncRequest,
    db: AsyncSession = Depends(get_db),
) -> PohodaSyncResult:
    """Sync an entity with Pohoda accounting system.

    Args:
        request: Sync request with entity type and ID
        db: Database session

    Returns:
        Sync result with status and Pohoda ID

    Raises:
        HTTPException: If entity not found or sync fails
    """
    service = PohodaService(db)

    try:
        if request.entity_type == "customer":
            sync_log = await service.sync_customer(request.entity_id)
        elif request.entity_type == "order":
            sync_log = await service.sync_order(request.entity_id)
        elif request.entity_type == "offer":
            sync_log = await service.sync_offer(request.entity_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported entity type: {request.entity_type}",
            )

        await db.commit()

        pohoda_id = None
        if sync_log.pohoda_doc_number:
            try:
                pohoda_id = int(sync_log.pohoda_doc_number)
            except (ValueError, TypeError):
                pass

        return PohodaSyncResult(
            success=sync_log.status == SyncStatus.SUCCESS,
            sync_log_id=sync_log.id,
            pohoda_id=pohoda_id,
            pohoda_doc_number=sync_log.pohoda_doc_number,
            error=sync_log.error_message,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/sync/{entity_type}/{entity_id}",
    response_model=PohodaSyncResult,
    status_code=status.HTTP_200_OK,
)
async def sync_entity_by_path(
    entity_type: str,
    entity_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PohodaSyncResult:
    """Sync an entity with Pohoda using path parameters.

    Args:
        entity_type: Entity type (customer, order, offer)
        entity_id: Entity UUID
        db: Database session

    Returns:
        Sync result
    """
    request = PohodaSyncRequest(entity_type=entity_type, entity_id=entity_id)
    return await sync_entity(request, db)


@router.get(
    "/status/{entity_type}/{entity_id}",
    response_model=PohodaSyncStatusResponse,
)
async def get_sync_status(
    entity_type: str,
    entity_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PohodaSyncStatusResponse:
    """Get Pohoda sync status for an entity.

    Args:
        entity_type: Entity type (customer, order, offer)
        entity_id: Entity UUID
        db: Database session

    Returns:
        Sync status with last sync info
    """
    service = PohodaService(db)
    status_data = await service.get_sync_status(entity_type, entity_id)
    return PohodaSyncStatusResponse(**status_data)


@router.get(
    "/logs",
    response_model=list[PohodaSyncLogResponse],
)
async def get_sync_logs(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[UUID] = Query(None, description="Filter by entity ID"),
    sync_status: Optional[SyncStatus] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[PohodaSyncLogResponse]:
    """Get Pohoda sync logs with optional filtering.

    Args:
        entity_type: Optional entity type filter
        entity_id: Optional entity ID filter
        sync_status: Optional status filter
        skip: Pagination offset
        limit: Maximum records to return
        db: Database session

    Returns:
        List of sync log entries
    """
    service = PohodaService(db)
    logs = await service.get_sync_logs(
        entity_type=entity_type,
        entity_id=entity_id,
        status=sync_status,
        skip=skip,
        limit=limit,
    )
    return [PohodaSyncLogResponse.model_validate(log) for log in logs]
