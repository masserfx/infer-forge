"""Orchestration API endpoints for DLQ management and pipeline monitoring."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import Date, case, cast, func, select, text

from app.core.database import AsyncSessionLocal
from app.models.dead_letter import DeadLetterEntry
from app.models.inbox import InboxMessage
from app.models.processing_task import ProcessingStage, ProcessingStatus, ProcessingTask

router = APIRouter(prefix="/orchestrace", tags=["orchestrace"])


# ─── Schemas ───────────────────────────────────────────────────

class TestEmailAttachment(BaseModel):
    filename: str
    content_type: str = "application/octet-stream"
    data_base64: str = Field(description="Base64-encoded file content")


class TestEmailRequest(BaseModel):
    from_email: str = Field(description="Sender email address")
    subject: str = Field(description="Email subject")
    body_text: str = Field(description="Email body text")
    attachments: list[TestEmailAttachment] = Field(default_factory=list)
    references_header: str | None = None
    in_reply_to_header: str | None = None


class TestEmailResponse(BaseModel):
    pipeline_stages: list[dict]
    inbox_message_id: str | None = None
    classification: str | None = None
    classification_confidence: float | None = None
    classification_method: str | None = None
    routed_stages: list[str] = Field(default_factory=list)
    customer_id: str | None = None
    order_id: str | None = None
    order_number: str | None = None
    attachment_count: int = 0
    total_time_ms: int = 0
    errors: list[str] = Field(default_factory=list)


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
    input_data: dict | None = None
    output_data: dict | None = None
    created_at: str

    class Config:
        from_attributes = True


class ProcessingTaskDetailResponse(ProcessingTaskResponse):
    order_id: str | None = None
    error_traceback: str | None = None


class PipelineStatsResponse(BaseModel):
    total_tasks: int
    by_stage: dict[str, int]
    by_status: dict[str, int]
    total_tokens_used: int
    avg_processing_time_ms: float
    error_rate: float
    dlq_unresolved: int


class TimelineBucket(BaseModel):
    bucket: str
    tasks_count: int
    success_count: int
    failed_count: int
    tokens_used: int


class PipelineConfigResponse(BaseModel):
    auto_calculate: bool
    auto_offer: bool
    auto_create_orders: bool
    review_threshold: float


class PipelineConfigUpdate(BaseModel):
    auto_calculate: bool | None = None
    auto_offer: bool | None = None
    auto_create_orders: bool | None = None
    review_threshold: float | None = Field(None, ge=0.0, le=1.0)


class PendingApprovalResponse(BaseModel):
    id: str
    order_id: str
    order_number: str
    customer_name: str | None
    name: str
    total_price: float
    note: str | None
    created_at: str


class ClassificationBucket(BaseModel):
    category: str
    count: int
    avg_confidence: float


class MethodBucket(BaseModel):
    method: str
    count: int
    avg_confidence: float
    avg_time_ms: float


class ConfidenceBucket(BaseModel):
    range: str
    count: int


class EntityField(BaseModel):
    field: str
    extracted_count: int
    total_count: int
    rate: float


class StageStat(BaseModel):
    stage: str
    total: int
    success: int
    failed: int
    avg_time_ms: float
    total_tokens: int


class TrendPoint(BaseModel):
    date: str
    avg_confidence: float
    email_count: int


class ValueCount(BaseModel):
    value: str
    count: int


class NLPAnalyticsResponse(BaseModel):
    period: str
    total_emails: int
    classification_distribution: list[ClassificationBucket]
    classification_methods: list[MethodBucket]
    escalation_rate: float
    avg_confidence: float
    confidence_buckets: list[ConfidenceBucket]
    entity_extraction: list[EntityField]
    stage_success_rates: list[StageStat]
    total_tokens: int
    tokens_by_stage: dict[str, int]
    confidence_trend: list[TrendPoint]
    top_materials: list[ValueCount]
    top_companies: list[ValueCount]


class DLQResolveRequest(BaseModel):
    resolved_by: str | None = None


class RejectRequest(BaseModel):
    reason: str | None = None


# ─── NLP Analytics Endpoint ──────────────────────────────────

@router.get("/nlp-analytics", response_model=NLPAnalyticsResponse)
async def get_nlp_analytics(
    period: str = Query("all", description="today|week|month|all"),
):
    """Get NLP analytics for the email processing pipeline."""
    cutoff = _period_cutoff(period)

    async with AsyncSessionLocal() as session:
        # Base filter for InboxMessage
        inbox_filter = InboxMessage.direction == "inbound"
        if cutoff:
            inbox_filter = inbox_filter & (InboxMessage.created_at >= cutoff)

        # Total emails
        total_emails = (await session.execute(
            select(func.count(InboxMessage.id)).where(inbox_filter)
        )).scalar() or 0

        # Classification distribution
        cls_q = (
            select(
                InboxMessage.classification,
                func.count(InboxMessage.id),
                func.coalesce(func.avg(InboxMessage.confidence), 0),
            )
            .where(inbox_filter)
            .where(InboxMessage.classification.isnot(None))
            .group_by(InboxMessage.classification)
            .order_by(func.count(InboxMessage.id).desc())
        )
        cls_rows = (await session.execute(cls_q)).all()
        classification_distribution = [
            ClassificationBucket(
                category=row[0].value if hasattr(row[0], "value") else str(row[0]),
                count=row[1],
                avg_confidence=round(float(row[2]), 3),
            )
            for row in cls_rows
        ]

        # Average confidence
        avg_conf = (await session.execute(
            select(func.coalesce(func.avg(InboxMessage.confidence), 0)).where(inbox_filter)
        )).scalar() or 0
        avg_confidence = round(float(avg_conf), 3)

        # Escalation rate (needs_review = true)
        escalated = (await session.execute(
            select(func.count(InboxMessage.id)).where(
                inbox_filter & (InboxMessage.needs_review == True)  # noqa: E712
            )
        )).scalar() or 0
        escalation_rate = round(escalated / total_emails, 3) if total_emails > 0 else 0.0

        # Confidence buckets
        confidence_ranges = [
            ("0-50%", 0.0, 0.5),
            ("50-60%", 0.5, 0.6),
            ("60-70%", 0.6, 0.7),
            ("70-80%", 0.7, 0.8),
            ("80-90%", 0.8, 0.9),
            ("90-100%", 0.9, 1.01),
        ]
        confidence_buckets = []
        for label, low, high in confidence_ranges:
            cnt = (await session.execute(
                select(func.count(InboxMessage.id)).where(
                    inbox_filter
                    & (InboxMessage.confidence.isnot(None))
                    & (InboxMessage.confidence >= low)
                    & (InboxMessage.confidence < high)
                )
            )).scalar() or 0
            confidence_buckets.append(ConfidenceBucket(range=label, count=cnt))

        # Classification methods from ProcessingTask (stage=classify)
        task_filter = ProcessingTask.stage == ProcessingStage.CLASSIFY
        if cutoff:
            task_filter = task_filter & (ProcessingTask.created_at >= cutoff)

        # We extract method from output_data->>'method'
        method_q = (
            select(
                func.coalesce(
                    ProcessingTask.output_data[text("'method'")].as_string(),
                    text("'unknown'"),
                ),
                func.count(ProcessingTask.id),
                func.coalesce(func.avg(
                    case(
                        (InboxMessage.confidence.isnot(None), InboxMessage.confidence),
                    )
                ), 0),
                func.coalesce(func.avg(ProcessingTask.processing_time_ms), 0),
            )
            .outerjoin(InboxMessage, ProcessingTask.inbox_message_id == InboxMessage.id)
            .where(task_filter)
            .where(ProcessingTask.status == ProcessingStatus.SUCCESS)
            .group_by(text("1"))
        )
        method_rows = (await session.execute(method_q)).all()
        classification_methods = [
            MethodBucket(
                method=str(row[0]),
                count=row[1],
                avg_confidence=round(float(row[2]), 3),
                avg_time_ms=round(float(row[3]), 1),
            )
            for row in method_rows
        ]

        # Entity extraction from parsed_data JSON
        entity_fields = [
            "company_name", "ico", "email", "phone", "items",
            "deadline", "urgency", "contact_person",
        ]
        entity_extraction = []
        for field in entity_fields:
            extracted = (await session.execute(
                select(func.count(InboxMessage.id)).where(
                    inbox_filter
                    & (InboxMessage.parsed_data.isnot(None))
                    & (InboxMessage.parsed_data[text(f"'{field}'")].isnot(None))
                )
            )).scalar() or 0
            total_parsed = (await session.execute(
                select(func.count(InboxMessage.id)).where(
                    inbox_filter & (InboxMessage.parsed_data.isnot(None))
                )
            )).scalar() or 0
            entity_extraction.append(EntityField(
                field=field,
                extracted_count=extracted,
                total_count=total_parsed,
                rate=round(extracted / total_parsed, 3) if total_parsed > 0 else 0.0,
            ))
        # Sort by rate descending
        entity_extraction.sort(key=lambda x: x.rate, reverse=True)

        # Stage success rates
        pt_filter = True  # noqa: E712
        if cutoff:
            pt_filter = ProcessingTask.created_at >= cutoff

        stage_q = (
            select(
                ProcessingTask.stage,
                func.count(ProcessingTask.id),
                func.count(case((ProcessingTask.status == ProcessingStatus.SUCCESS, 1))),
                func.count(case((ProcessingTask.status.in_(
                    [ProcessingStatus.FAILED, ProcessingStatus.DLQ]
                ), 1))),
                func.coalesce(func.avg(ProcessingTask.processing_time_ms), 0),
                func.coalesce(func.sum(ProcessingTask.tokens_used), 0),
            )
            .where(pt_filter)
            .group_by(ProcessingTask.stage)
            .order_by(ProcessingTask.stage)
        )
        stage_rows = (await session.execute(stage_q)).all()
        stage_success_rates = [
            StageStat(
                stage=row[0].value,
                total=row[1],
                success=row[2],
                failed=row[3],
                avg_time_ms=round(float(row[4]), 1),
                total_tokens=row[5],
            )
            for row in stage_rows
        ]

        # Total tokens and tokens by stage
        total_tokens = sum(s.total_tokens for s in stage_success_rates)
        tokens_by_stage = {s.stage: s.total_tokens for s in stage_success_rates}

        # Confidence trend by date
        trend_q = (
            select(
                cast(InboxMessage.created_at, Date).label("date"),
                func.coalesce(func.avg(InboxMessage.confidence), 0),
                func.count(InboxMessage.id),
            )
            .where(inbox_filter)
            .where(InboxMessage.confidence.isnot(None))
            .group_by(text("date"))
            .order_by(text("date"))
        )
        trend_rows = (await session.execute(trend_q)).all()
        confidence_trend = [
            TrendPoint(
                date=str(row[0]),
                avg_confidence=round(float(row[1]), 3),
                email_count=row[2],
            )
            for row in trend_rows
        ]

        # Top companies from parsed_data->>'company_name'
        company_q = (
            select(
                InboxMessage.parsed_data[text("'company_name'")].as_string(),
                func.count(InboxMessage.id),
            )
            .where(
                inbox_filter
                & (InboxMessage.parsed_data.isnot(None))
                & (InboxMessage.parsed_data[text("'company_name'")].isnot(None))
            )
            .group_by(text("1"))
            .order_by(func.count(InboxMessage.id).desc())
            .limit(10)
        )
        company_rows = (await session.execute(company_q)).all()
        top_companies = [
            ValueCount(value=str(row[0]), count=row[1])
            for row in company_rows
            if row[0]
        ]

        # Top materials from parsed_data->'items' (JSON array with 'material' key)
        # This requires iterating parsed_data; we'll do it in Python
        material_q = (
            select(InboxMessage.parsed_data)
            .where(
                inbox_filter
                & (InboxMessage.parsed_data.isnot(None))
            )
        )
        material_rows = (await session.execute(material_q)).all()
        material_counts: dict[str, int] = {}
        for (pd,) in material_rows:
            if isinstance(pd, dict):
                items = pd.get("items", [])
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            mat = item.get("material")
                            if mat and isinstance(mat, str):
                                material_counts[mat] = material_counts.get(mat, 0) + 1
        top_materials = [
            ValueCount(value=k, count=v)
            for k, v in sorted(material_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        return NLPAnalyticsResponse(
            period=period,
            total_emails=total_emails,
            classification_distribution=classification_distribution,
            classification_methods=classification_methods,
            escalation_rate=escalation_rate,
            avg_confidence=avg_confidence,
            confidence_buckets=confidence_buckets,
            entity_extraction=entity_extraction,
            stage_success_rates=stage_success_rates,
            total_tokens=total_tokens,
            tokens_by_stage=tokens_by_stage,
            confidence_trend=confidence_trend,
            top_materials=top_materials,
            top_companies=top_companies,
        )


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
            "orchestration.analyze_drawing": orch_tasks.analyze_drawing,
            "orchestration.orchestrate_order": orch_tasks.orchestrate_order,
            "orchestration.auto_calculate": orch_tasks.auto_calculate,
            "orchestration.generate_offer": orch_tasks.generate_offer,
        }

        task_func = task_map.get(entry.original_task)
        if not task_func:
            raise HTTPException(status_code=400, detail=f"Unknown task: {entry.original_task}")

        # Re-dispatch with task-specific argument unpacking
        if entry.payload:
            if entry.original_task == "orchestration.process_attachment":
                p = entry.payload
                task_func.delay(
                    p.get("attachment_id", ""),
                    p.get("file_path", ""),
                    p.get("content_type", ""),
                    p.get("filename", ""),
                )
            elif entry.original_task == "orchestration.analyze_drawing":
                p = entry.payload
                task_func.delay(
                    p.get("document_id", ""),
                    p.get("ocr_text", ""),
                    p.get("ocr_confidence", 0.0),
                )
            elif isinstance(entry.payload, dict):
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
    date_from: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    date_to: str | None = Query(None, description="ISO date YYYY-MM-DD"),
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
        if date_from:
            query = query.where(
                ProcessingTask.created_at >= datetime.fromisoformat(date_from)
            )
        if date_to:
            query = query.where(
                ProcessingTask.created_at < datetime.fromisoformat(date_to) + timedelta(days=1)
            )

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
                input_data=t.input_data,
                output_data=t.output_data,
                created_at=t.created_at.isoformat(),
            )
            for t in tasks
        ]


@router.get("/tasks/{task_id}", response_model=ProcessingTaskDetailResponse)
async def get_processing_task(task_id: UUID):
    """Get processing task detail including input/output data."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ProcessingTask).where(ProcessingTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Try to extract order_id from output_data
        order_id = None
        if task.output_data and isinstance(task.output_data, dict):
            order_id = task.output_data.get("order_id")

        # Try to find error traceback from DLQ
        error_traceback = None
        if task.status == ProcessingStatus.DLQ or task.status == ProcessingStatus.FAILED:
            dlq_result = await session.execute(
                select(DeadLetterEntry.error_traceback)
                .where(DeadLetterEntry.original_task.contains(task.stage.value))
                .where(DeadLetterEntry.created_at >= task.created_at)
                .order_by(DeadLetterEntry.created_at.asc())
                .limit(1)
            )
            row = dlq_result.first()
            if row:
                error_traceback = row[0]

        return ProcessingTaskDetailResponse(
            id=str(task.id),
            inbox_message_id=str(task.inbox_message_id) if task.inbox_message_id else None,
            celery_task_id=task.celery_task_id,
            stage=task.stage.value,
            status=task.status.value,
            tokens_used=task.tokens_used,
            processing_time_ms=task.processing_time_ms,
            retry_count=task.retry_count,
            error_message=task.error_message,
            input_data=task.input_data,
            output_data=task.output_data,
            created_at=task.created_at.isoformat(),
            order_id=order_id,
            error_traceback=error_traceback,
        )


# ─── Pipeline Stats ──────────────────────────────────────────

def _period_cutoff(period: str | None) -> datetime | None:
    """Calculate cutoff datetime for a given period."""
    if not period or period == "all":
        return None
    now = datetime.now(UTC)
    if period == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        return now - timedelta(days=7)
    if period == "month":
        return now - timedelta(days=30)
    return None


@router.get("/stats", response_model=PipelineStatsResponse)
async def get_pipeline_stats(
    period: str | None = Query(None, description="today|week|month|all"),
):
    """Get pipeline processing statistics."""
    cutoff = _period_cutoff(period)

    async with AsyncSessionLocal() as session:
        base = select(ProcessingTask)
        if cutoff:
            base = base.where(ProcessingTask.created_at >= cutoff)

        # Total tasks
        total = (await session.execute(
            select(func.count(ProcessingTask.id)).where(
                ProcessingTask.created_at >= cutoff if cutoff else True  # noqa: E712
            )
        )).scalar() or 0

        # By stage
        stage_q = (
            select(ProcessingTask.stage, func.count(ProcessingTask.id))
            .group_by(ProcessingTask.stage)
        )
        if cutoff:
            stage_q = stage_q.where(ProcessingTask.created_at >= cutoff)
        stage_result = await session.execute(stage_q)
        by_stage = {row[0].value: row[1] for row in stage_result}

        # By status
        status_q = (
            select(ProcessingTask.status, func.count(ProcessingTask.id))
            .group_by(ProcessingTask.status)
        )
        if cutoff:
            status_q = status_q.where(ProcessingTask.created_at >= cutoff)
        status_result = await session.execute(status_q)
        by_status = {row[0].value: row[1] for row in status_result}

        # Tokens
        tokens_q = select(func.coalesce(func.sum(ProcessingTask.tokens_used), 0))
        if cutoff:
            tokens_q = tokens_q.where(ProcessingTask.created_at >= cutoff)
        tokens = (await session.execute(tokens_q)).scalar() or 0

        # Average processing time
        avg_q = select(func.coalesce(func.avg(ProcessingTask.processing_time_ms), 0))
        if cutoff:
            avg_q = avg_q.where(ProcessingTask.created_at >= cutoff)
        avg_time = (await session.execute(avg_q)).scalar() or 0

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


@router.get("/stats/timeline", response_model=list[TimelineBucket])
async def get_pipeline_timeline(
    period: str = Query("today", description="today|week|month"),
):
    """Get time-series stats (group by hour for today, by day for week/month)."""
    from sqlalchemy import case, cast, Date, extract, literal_column

    now = datetime.now(UTC)
    if period == "today":
        cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        cutoff = now - timedelta(days=7)
    else:
        cutoff = now - timedelta(days=30)

    async with AsyncSessionLocal() as session:
        if period == "today":
            # Group by hour
            bucket_expr = extract("hour", ProcessingTask.created_at)
        else:
            # Group by date
            bucket_expr = cast(ProcessingTask.created_at, Date)

        q = (
            select(
                bucket_expr.label("bucket"),
                func.count(ProcessingTask.id).label("tasks_count"),
                func.count(
                    case(
                        (ProcessingTask.status == ProcessingStatus.SUCCESS, 1),
                    )
                ).label("success_count"),
                func.count(
                    case(
                        (ProcessingTask.status.in_([ProcessingStatus.FAILED, ProcessingStatus.DLQ]), 1),
                    )
                ).label("failed_count"),
                func.coalesce(func.sum(ProcessingTask.tokens_used), 0).label("tokens_used"),
            )
            .where(ProcessingTask.created_at >= cutoff)
            .group_by(literal_column("bucket"))
            .order_by(literal_column("bucket"))
        )

        result = await session.execute(q)
        rows = result.all()

        return [
            TimelineBucket(
                bucket=str(row.bucket),
                tasks_count=row.tasks_count,
                success_count=row.success_count,
                failed_count=row.failed_count,
                tokens_used=row.tokens_used,
            )
            for row in rows
        ]


# ─── Pipeline Config ─────────────────────────────────────────

@router.get("/config", response_model=PipelineConfigResponse)
async def get_pipeline_config():
    """Get current pipeline configuration flags."""
    from app.core.config import get_settings

    settings = get_settings()
    return PipelineConfigResponse(
        auto_calculate=settings.ORCHESTRATION_AUTO_CALCULATE,
        auto_offer=settings.ORCHESTRATION_AUTO_OFFER,
        auto_create_orders=settings.ORCHESTRATION_AUTO_CREATE_ORDERS,
        review_threshold=settings.ORCHESTRATION_REVIEW_THRESHOLD,
    )


@router.put("/config", response_model=PipelineConfigResponse)
async def update_pipeline_config(body: PipelineConfigUpdate):
    """Update pipeline configuration flags (runtime, persisted in settings singleton)."""
    from app.core.config import get_settings

    settings = get_settings()
    if body.auto_calculate is not None:
        object.__setattr__(settings, "ORCHESTRATION_AUTO_CALCULATE", body.auto_calculate)
    if body.auto_offer is not None:
        object.__setattr__(settings, "ORCHESTRATION_AUTO_OFFER", body.auto_offer)
    if body.auto_create_orders is not None:
        object.__setattr__(settings, "ORCHESTRATION_AUTO_CREATE_ORDERS", body.auto_create_orders)
    if body.review_threshold is not None:
        object.__setattr__(settings, "ORCHESTRATION_REVIEW_THRESHOLD", body.review_threshold)

    return PipelineConfigResponse(
        auto_calculate=settings.ORCHESTRATION_AUTO_CALCULATE,
        auto_offer=settings.ORCHESTRATION_AUTO_OFFER,
        auto_create_orders=settings.ORCHESTRATION_AUTO_CREATE_ORDERS,
        review_threshold=settings.ORCHESTRATION_REVIEW_THRESHOLD,
    )


# ─── Approval Workflow ───────────────────────────────────────

@router.get("/pending-approvals", response_model=list[PendingApprovalResponse])
async def list_pending_approvals():
    """List calculations awaiting approval."""
    from app.models.calculation import Calculation, CalculationStatus
    from app.models.customer import Customer
    from app.models.order import Order

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Calculation, Order, Customer)
            .join(Order, Calculation.order_id == Order.id)
            .outerjoin(Customer, Order.customer_id == Customer.id)
            .where(Calculation.status == CalculationStatus.PENDING_APPROVAL)
            .order_by(Calculation.created_at.desc())
        )
        rows = result.all()

        return [
            PendingApprovalResponse(
                id=str(calc.id),
                order_id=str(order.id),
                order_number=order.number,
                customer_name=customer.company_name if customer else None,
                name=calc.name,
                total_price=float(calc.total_price),
                note=calc.note,
                created_at=calc.created_at.isoformat(),
            )
            for calc, order, customer in rows
        ]


@router.post("/approve-calculation/{calc_id}")
async def approve_calculation(calc_id: UUID):
    """Approve a pending calculation and optionally trigger offer generation."""
    from app.models.calculation import Calculation, CalculationStatus

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Calculation).where(Calculation.id == calc_id)
        )
        calc = result.scalar_one_or_none()
        if not calc:
            raise HTTPException(status_code=404, detail="Calculation not found")
        if calc.status != CalculationStatus.PENDING_APPROVAL:
            raise HTTPException(status_code=400, detail="Calculation is not pending approval")

        calc.status = CalculationStatus.APPROVED
        await session.commit()

        # Trigger offer generation if auto_offer is enabled
        from app.core.config import get_settings

        if get_settings().ORCHESTRATION_AUTO_OFFER:
            try:
                from app.orchestration.tasks import generate_offer
                generate_offer.delay(str(calc.order_id))
            except Exception:
                pass  # Non-critical: offer can be generated manually

        return {"status": "approved", "id": str(calc_id)}


@router.post("/reject-calculation/{calc_id}")
async def reject_calculation(calc_id: UUID, body: RejectRequest):
    """Reject a pending calculation with optional reason."""
    from app.models.calculation import Calculation, CalculationStatus

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Calculation).where(Calculation.id == calc_id)
        )
        calc = result.scalar_one_or_none()
        if not calc:
            raise HTTPException(status_code=404, detail="Calculation not found")
        if calc.status != CalculationStatus.PENDING_APPROVAL:
            raise HTTPException(status_code=400, detail="Calculation is not pending approval")

        calc.status = CalculationStatus.REJECTED
        if body.reason:
            calc.note = f"Zamítnuto: {body.reason}"
        await session.commit()

        return {"status": "rejected", "id": str(calc_id)}


# ─── Test Email Endpoint ─────────────────────────────────────


@router.post("/test-email", response_model=TestEmailResponse)
async def test_email_pipeline(body: TestEmailRequest):
    """Simulate email arrival and run the full orchestration pipeline.

    Runs all stages synchronously (no Celery) so the result is immediate.
    Useful for testing the pipeline without IMAP configuration.
    """
    from uuid import uuid4

    start = time.time()
    stages: list[dict] = []
    errors: list[str] = []
    result = TestEmailResponse(pipeline_stages=[], attachment_count=len(body.attachments))

    # ── Stage 1: Ingestion ──────────────────────────────────
    try:
        t0 = time.time()
        from app.orchestration.agents.email_ingestion import EmailIngestionAgent

        agent = EmailIngestionAgent()
        raw_email_data = {
            "message_id": f"<test-{uuid4()}@infer-forge-test>",
            "from_email": body.from_email,
            "subject": body.subject,
            "body_text": body.body_text,
            "received_at": datetime.now(UTC).isoformat(),
            "attachments": [
                {
                    "filename": att.filename,
                    "content_type": att.content_type,
                    "data_b64": att.data_base64,
                }
                for att in body.attachments
            ],
            "references_header": body.references_header,
            "in_reply_to_header": body.in_reply_to_header,
        }

        ingest_result = await agent.process_from_dict(raw_email_data)
        elapsed = int((time.time() - t0) * 1000)
        stages.append({
            "stage": "ingest",
            "status": "success",
            "time_ms": elapsed,
            "inbox_message_id": ingest_result["inbox_message_id"],
            "attachments": len(ingest_result.get("attachment_ids", [])),
            "thread_id": ingest_result.get("thread_id"),
        })
        result.inbox_message_id = ingest_result["inbox_message_id"]

    except Exception as e:
        errors.append(f"Ingestion failed: {e}")
        stages.append({"stage": "ingest", "status": "failed", "error": str(e)})
        result.pipeline_stages = stages
        result.errors = errors
        result.total_time_ms = int((time.time() - start) * 1000)
        return result

    # ── Stage 2: Classification ─────────────────────────────
    try:
        t0 = time.time()
        from app.orchestration.agents.heuristic_classifier import HeuristicClassifier

        hc = HeuristicClassifier()
        hc_result = hc.classify(
            subject=body.subject,
            body=body.body_text,
            has_attachments=len(body.attachments) > 0,
            body_length=len(body.body_text),
        )

        if hc_result:
            classification = hc_result.category
            confidence = hc_result.confidence
            method = "heuristic"
        else:
            # Fallback: try AI classifier if available
            try:
                from app.core.config import get_settings

                settings = get_settings()
                if settings.ANTHROPIC_API_KEY:
                    from app.agents.email_classifier import EmailClassifier

                    classifier = EmailClassifier(api_key=settings.ANTHROPIC_API_KEY)
                    ai_result = await classifier.classify(
                        subject=body.subject,
                        body=body.body_text,
                    )
                    classification = ai_result.category
                    confidence = ai_result.confidence
                    method = "ai_claude"
                else:
                    classification = "dotaz"
                    confidence = 0.5
                    method = "default_fallback"
            except Exception:
                classification = "dotaz"
                confidence = 0.5
                method = "default_fallback"

        elapsed = int((time.time() - t0) * 1000)
        stages.append({
            "stage": "classify",
            "status": "success",
            "time_ms": elapsed,
            "category": classification,
            "confidence": confidence,
            "method": method,
        })
        result.classification = classification
        result.classification_confidence = confidence
        result.classification_method = method

    except Exception as e:
        errors.append(f"Classification failed: {e}")
        stages.append({"stage": "classify", "status": "failed", "error": str(e)})
        result.pipeline_stages = stages
        result.errors = errors
        result.total_time_ms = int((time.time() - start) * 1000)
        return result

    # ── Stage 3: Routing ────────────────────────────────────
    try:
        from app.orchestration.router import route_classification

        routed_stages = route_classification(
            classification=classification,
            confidence=confidence,
            has_attachments=len(body.attachments) > 0,
        )
        stages.append({
            "stage": "route",
            "status": "success",
            "routed_to": routed_stages,
        })
        result.routed_stages = routed_stages

    except Exception as e:
        errors.append(f"Routing failed: {e}")
        stages.append({"stage": "route", "status": "failed", "error": str(e)})
        routed_stages = []

    # ── Stage 4: Attachment Processing ──────────────────────
    if "process_attachments" in routed_stages and ingest_result.get("attachment_ids"):
        try:
            t0 = time.time()
            from app.models.email_attachment import EmailAttachment
            from app.orchestration.agents.attachment_processor import AttachmentProcessor

            ap = AttachmentProcessor()
            att_results = []
            for att_id_str in ingest_result["attachment_ids"]:
                async with AsyncSessionLocal() as session:
                    att_row = (await session.execute(
                        select(EmailAttachment).where(
                            EmailAttachment.id == UUID(att_id_str)
                        )
                    )).scalar_one()

                try:
                    att_result = await ap.process(
                        attachment_id=UUID(att_id_str),
                        file_path=att_row.file_path,
                        content_type=att_row.content_type,
                        filename=att_row.filename,
                    )
                    att_results.append(att_result)
                except Exception as att_err:
                    att_results.append({"error": str(att_err), "filename": att_row.filename})

            elapsed = int((time.time() - t0) * 1000)
            stages.append({
                "stage": "process_attachments",
                "status": "success",
                "time_ms": elapsed,
                "results": att_results,
            })
        except Exception as e:
            errors.append(f"Attachment processing failed: {e}")
            stages.append({"stage": "process_attachments", "status": "failed", "error": str(e)})

    # ── Stage 5: Order Orchestration ────────────────────────
    if "orchestrate_order" in routed_stages:
        try:
            t0 = time.time()
            from app.orchestration.agents.order_orchestrator import OrderOrchestrator

            oo = OrderOrchestrator()
            orch_result = await oo.process(
                inbox_message_id=UUID(ingest_result["inbox_message_id"]),
                parsed_data={
                    "classification": classification,
                    "company_name": None,
                    "contact_email": body.from_email,
                    "ico": None,
                },
            )
            elapsed = int((time.time() - t0) * 1000)
            stages.append({
                "stage": "orchestrate_order",
                "status": "success",
                "time_ms": elapsed,
                "customer_id": orch_result.get("customer_id"),
                "order_id": orch_result.get("order_id"),
                "order_number": orch_result.get("order_number"),
                "customer_created": orch_result.get("customer_created"),
                "order_created": orch_result.get("order_created"),
                "next_stage": orch_result.get("next_stage"),
            })
            result.customer_id = orch_result.get("customer_id")
            result.order_id = orch_result.get("order_id")
            result.order_number = orch_result.get("order_number")

        except Exception as e:
            errors.append(f"Order orchestration failed: {e}")
            stages.append({"stage": "orchestrate_order", "status": "failed", "error": str(e)})

    # ── Stage 6: Archive ────────────────────────────────────
    if "archive" in routed_stages:
        try:
            from app.models.inbox import InboxMessage, InboxStatus

            async with AsyncSessionLocal() as session:
                msg = (await session.execute(
                    select(InboxMessage).where(
                        InboxMessage.id == UUID(ingest_result["inbox_message_id"])
                    )
                )).scalar_one()
                msg.status = InboxStatus.ARCHIVED
                await session.commit()

            stages.append({"stage": "archive", "status": "success"})
        except Exception as e:
            errors.append(f"Archive failed: {e}")
            stages.append({"stage": "archive", "status": "failed", "error": str(e)})

    # ── Stage 7: Escalate ───────────────────────────────────
    if "escalate" in routed_stages:
        try:
            from app.models.inbox import InboxMessage, InboxStatus

            async with AsyncSessionLocal() as session:
                msg = (await session.execute(
                    select(InboxMessage).where(
                        InboxMessage.id == UUID(ingest_result["inbox_message_id"])
                    )
                )).scalar_one()
                msg.status = InboxStatus.ESCALATED
                msg.needs_review = True
                await session.commit()

            stages.append({"stage": "escalate", "status": "success"})
        except Exception as e:
            errors.append(f"Escalate failed: {e}")
            stages.append({"stage": "escalate", "status": "failed", "error": str(e)})

    result.pipeline_stages = stages
    result.errors = errors
    result.total_time_ms = int((time.time() - start) * 1000)
    return result


@router.post("/batch-upload")
async def batch_upload_eml(
    files: list[UploadFile] = File(...),
):
    """Upload multiple EML files and dispatch them to the orchestration pipeline.

    Each EML file is parsed and dispatched as a run_pipeline task.
    """
    import email as email_module
    from uuid import uuid4

    results = []

    for upload_file in files:
        try:
            content = await upload_file.read()
            msg = email_module.message_from_bytes(content)

            # Extract basic headers
            message_id = msg.get("Message-ID", f"<batch-{uuid4()}@infer-forge>")
            from_email = msg.get("From", "unknown@unknown.com")
            subject = msg.get("Subject", "(bez předmětu)")

            # Extract body
            body_text = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition", "")):
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            body_text = payload.decode(charset, errors="replace")
                            break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or "utf-8"
                    body_text = payload.decode(charset, errors="replace")

            raw_email_data = {
                "message_id": message_id,
                "from_email": from_email,
                "subject": subject,
                "body_text": body_text,
                "received_at": datetime.now(UTC).isoformat(),
                "attachments": [],
                "references_header": msg.get("References"),
                "in_reply_to_header": msg.get("In-Reply-To"),
            }

            from app.orchestration.tasks import run_pipeline
            task = run_pipeline.delay(raw_email_data)

            results.append({
                "filename": upload_file.filename,
                "status": "dispatched",
                "task_id": task.id,
                "message_id": message_id,
                "subject": subject,
            })
        except Exception as e:
            results.append({
                "filename": upload_file.filename,
                "status": "failed",
                "error": str(e),
            })

    return {
        "total": len(files),
        "dispatched": sum(1 for r in results if r["status"] == "dispatched"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "results": results,
    }
