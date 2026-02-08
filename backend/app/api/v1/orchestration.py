"""Orchestration API endpoints for DLQ management and pipeline monitoring."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.dead_letter import DeadLetterEntry
from app.models.processing_task import ProcessingStage, ProcessingStatus, ProcessingTask

router = APIRouter(prefix="/orchestrace", tags=["orchestrace"])


# ─── Schemas ───────────────────────────────────────────────────

class DLQEntryResponse(BaseModel):
    id: str
    original_task: str
    stage: str
    error_message: str | None
    retry_count: int
    resolved: bool
    resolved_at: str | None
    created_at: str

    class Config:
        from_attributes = True


class DLQListResponse(BaseModel):
    items: list[DLQEntryResponse]
    total: int
    unresolved: int


class ProcessingTaskResponse(BaseModel):
    id: str
    inbox_message_id: str | None
    celery_task_id: str | None
    stage: str
    status: str
    tokens_used: int | None
    processing_time_ms: int | None
    retry_count: int
    error_message: str | None
    created_at: str

    class Config:
        from_attributes = True


class PipelineStatsResponse(BaseModel):
    total_tasks: int
    by_stage: dict[str, int]
    by_status: dict[str, int]
    total_tokens_used: int
    avg_processing_time_ms: float
    error_rate: float
    dlq_unresolved: int


class DLQResolveRequest(BaseModel):
    resolved_by: str | None = None


# ─── DLQ Endpoints ────────────────────────────────────────────

@router.get("/dlq", response_model=DLQListResponse)
async def list_dlq_entries(
    resolved: bool | None = Query(None),
    stage: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List dead letter queue entries."""
    async with AsyncSessionLocal() as session:
        query = select(DeadLetterEntry).order_by(DeadLetterEntry.created_at.desc())
        count_query = select(func.count(DeadLetterEntry.id))
        unresolved_query = select(func.count(DeadLetterEntry.id)).where(
            DeadLetterEntry.resolved == False  # noqa: E712
        )

        if resolved is not None:
            query = query.where(DeadLetterEntry.resolved == resolved)
            count_query = count_query.where(DeadLetterEntry.resolved == resolved)
        if stage:
            query = query.where(DeadLetterEntry.stage == stage)
            count_query = count_query.where(DeadLetterEntry.stage == stage)

        query = query.limit(limit).offset(offset)

        result = await session.execute(query)
        entries = result.scalars().all()

        total = (await session.execute(count_query)).scalar() or 0
        unresolved = (await session.execute(unresolved_query)).scalar() or 0

        return DLQListResponse(
            items=[
                DLQEntryResponse(
                    id=str(e.id),
                    original_task=e.original_task,
                    stage=e.stage,
                    error_message=e.error_message,
                    retry_count=e.retry_count,
                    resolved=e.resolved,
                    resolved_at=e.resolved_at.isoformat() if e.resolved_at else None,
                    created_at=e.created_at.isoformat(),
                )
                for e in entries
            ],
            total=total,
            unresolved=unresolved,
        )


@router.get("/dlq/{entry_id}")
async def get_dlq_entry(entry_id: UUID):
    """Get DLQ entry detail including payload and traceback."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DeadLetterEntry).where(DeadLetterEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise HTTPException(status_code=404, detail="DLQ entry not found")

        return {
            "id": str(entry.id),
            "original_task": entry.original_task,
            "stage": entry.stage,
            "payload": entry.payload,
            "error_message": entry.error_message,
            "error_traceback": entry.error_traceback,
            "retry_count": entry.retry_count,
            "resolved": entry.resolved,
            "resolved_at": entry.resolved_at.isoformat() if entry.resolved_at else None,
            "resolved_by": str(entry.resolved_by) if entry.resolved_by else None,
            "created_at": entry.created_at.isoformat(),
        }


@router.post("/dlq/{entry_id}/resolve")
async def resolve_dlq_entry(entry_id: UUID, body: DLQResolveRequest):
    """Mark a DLQ entry as resolved."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DeadLetterEntry).where(DeadLetterEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise HTTPException(status_code=404, detail="DLQ entry not found")

        entry.resolved = True
        entry.resolved_at = datetime.now(UTC)
        if body.resolved_by:
            try:
                entry.resolved_by = UUID(body.resolved_by)
            except ValueError:
                pass

        await session.commit()
        return {"status": "resolved", "id": str(entry_id)}


@router.post("/dlq/{entry_id}/retry")
async def retry_dlq_entry(entry_id: UUID):
    """Retry a failed DLQ entry by re-dispatching the task."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DeadLetterEntry).where(DeadLetterEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise HTTPException(status_code=404, detail="DLQ entry not found")

        if entry.resolved:
            raise HTTPException(status_code=400, detail="Entry already resolved")

        # Re-dispatch based on original task
        from app.orchestration import tasks as orch_tasks

        task_map = {
            "orchestration.ingest_email": orch_tasks.ingest_email,
            "orchestration.classify_email": orch_tasks.classify_email,
            "orchestration.parse_email": orch_tasks.parse_email,
            "orchestration.process_attachment": orch_tasks.process_attachment,
            "orchestration.orchestrate_order": orch_tasks.orchestrate_order,
            "orchestration.auto_calculate": orch_tasks.auto_calculate,
            "orchestration.generate_offer": orch_tasks.generate_offer,
        }

        task_func = task_map.get(entry.original_task)
        if not task_func:
            raise HTTPException(status_code=400, detail=f"Unknown task: {entry.original_task}")

        # Re-dispatch
        if entry.payload:
            if isinstance(entry.payload, dict):
                task_func.delay(entry.payload)
            elif isinstance(entry.payload, list):
                task_func.delay(*entry.payload)

        entry.retry_count += 1
        await session.commit()

        return {"status": "retried", "id": str(entry_id), "retry_count": entry.retry_count}


# ─── Processing Tasks Endpoints ───────────────────────────────

@router.get("/tasks", response_model=list[ProcessingTaskResponse])
async def list_processing_tasks(
    stage: str | None = Query(None),
    status: str | None = Query(None),
    inbox_message_id: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List processing tasks (audit trail)."""
    async with AsyncSessionLocal() as session:
        query = select(ProcessingTask).order_by(ProcessingTask.created_at.desc())

        if stage:
            query = query.where(ProcessingTask.stage == ProcessingStage(stage))
        if status:
            query = query.where(ProcessingTask.status == ProcessingStatus(status))
        if inbox_message_id:
            query = query.where(ProcessingTask.inbox_message_id == inbox_message_id)

        query = query.limit(limit).offset(offset)

        result = await session.execute(query)
        tasks = result.scalars().all()

        return [
            ProcessingTaskResponse(
                id=str(t.id),
                inbox_message_id=str(t.inbox_message_id) if t.inbox_message_id else None,
                celery_task_id=t.celery_task_id,
                stage=t.stage.value,
                status=t.status.value,
                tokens_used=t.tokens_used,
                processing_time_ms=t.processing_time_ms,
                retry_count=t.retry_count,
                error_message=t.error_message,
                created_at=t.created_at.isoformat(),
            )
            for t in tasks
        ]


# ─── Pipeline Stats ──────────────────────────────────────────

@router.get("/stats", response_model=PipelineStatsResponse)
async def get_pipeline_stats():
    """Get pipeline processing statistics."""
    async with AsyncSessionLocal() as session:
        # Total tasks
        total = (await session.execute(
            select(func.count(ProcessingTask.id))
        )).scalar() or 0

        # By stage
        stage_result = await session.execute(
            select(ProcessingTask.stage, func.count(ProcessingTask.id))
            .group_by(ProcessingTask.stage)
        )
        by_stage = {row[0].value: row[1] for row in stage_result}

        # By status
        status_result = await session.execute(
            select(ProcessingTask.status, func.count(ProcessingTask.id))
            .group_by(ProcessingTask.status)
        )
        by_status = {row[0].value: row[1] for row in status_result}

        # Tokens
        tokens = (await session.execute(
            select(func.coalesce(func.sum(ProcessingTask.tokens_used), 0))
        )).scalar() or 0

        # Average processing time
        avg_time = (await session.execute(
            select(func.coalesce(func.avg(ProcessingTask.processing_time_ms), 0))
        )).scalar() or 0

        # Error rate
        failed = by_status.get("failed", 0) + by_status.get("dlq", 0)
        error_rate = failed / total if total > 0 else 0.0

        # DLQ unresolved
        dlq_unresolved = (await session.execute(
            select(func.count(DeadLetterEntry.id)).where(
                DeadLetterEntry.resolved == False  # noqa: E712
            )
        )).scalar() or 0

        return PipelineStatsResponse(
            total_tasks=total,
            by_stage=by_stage,
            by_status=by_status,
            total_tokens_used=tokens,
            avg_processing_time_ms=float(avg_time),
            error_rate=error_rate,
            dlq_unresolved=dlq_unresolved,
        )
